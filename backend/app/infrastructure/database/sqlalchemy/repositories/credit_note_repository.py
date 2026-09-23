from __future__ import annotations

"""SQLAlchemy adapter for credit and debit note persistence, allocations, and GL posting."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.application.credit_notes.dto import (
    AllocateCreditNoteCommand,
    CreateCreditNoteAllocationCommand,
    CreateCreditNoteCommand,
    CreditNoteAllocationDTO,
    CreditNoteDTO,
    CreditNoteLineDTO,
    CreditNotePageDTO,
    CreditNoteQuery,
    PostCreditNoteCommand,
    VoidCreditNoteCommand,
)
from app.application.credit_notes.ports import CreditNoteRepository
from app.core.database import flush_or_rollback
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.credit_note import (
    CreditNote,
    CreditNoteAllocation,
    CreditNoteLine,
)
from app.modules.accounting.models.invoice import Invoice
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.partner import Partner
from app.modules.accounting.models.payment import PaymentAllocation


class SqlAlchemyCreditNoteRepository(CreditNoteRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _line_to_dto(line: CreditNoteLine) -> CreditNoteLineDTO:
        return CreditNoteLineDTO(
            id=line.id,
            credit_note_id=line.credit_note_id,
            line_no=line.line_no,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            subtotal=line.subtotal,
            account_id=line.account_id,
        )

    @staticmethod
    def _allocation_to_dto(alloc: CreditNoteAllocation) -> CreditNoteAllocationDTO:
        invoice_no = alloc.invoice.invoice_no if alloc.invoice else None
        return CreditNoteAllocationDTO(
            id=alloc.id,
            company_id=alloc.company_id,
            credit_note_id=alloc.credit_note_id,
            invoice_id=alloc.invoice_id,
            amount=alloc.amount,
            created_at=alloc.created_at,
            invoice_no=invoice_no,
        )

    @classmethod
    def _to_dto(cls, cn: CreditNote) -> CreditNoteDTO:
        partner_name = cn.partner.name if cn.partner else None
        lines_dto = [cls._line_to_dto(l) for l in cn.lines]
        allocations_dto = [cls._allocation_to_dto(a) for a in cn.allocations]
        allocated_amount = sum((a.amount for a in cn.allocations), Decimal("0.00"))
        unallocated_amount = max(Decimal("0.00"), cn.total_amount - allocated_amount)

        return CreditNoteDTO(
            id=cn.id,
            company_id=cn.company_id,
            partner_id=cn.partner_id,
            note_type=cn.note_type,
            credit_note_no=cn.credit_note_no,
            issue_date=cn.issue_date,
            currency=cn.currency,
            status=cn.status,
            subtotal=cn.subtotal,
            tax_amount=cn.tax_amount,
            total_amount=cn.total_amount,
            allocated_amount=allocated_amount,
            unallocated_amount=unallocated_amount,
            reference=cn.reference,
            partner_name=partner_name,
            journal_entry_id=cn.journal_entry_id,
            reason=cn.reason,
            created_by_user_id=cn.created_by_user_id,
            created_at=cn.created_at,
            updated_at=cn.updated_at,
            lines=lines_dto,
            allocations=allocations_dto,
        )

    def create(self, command: CreateCreditNoteCommand) -> CreditNoteDTO:
        if not command.lines:
            raise ValueError("A credit note must contain at least one line item.")

        partner = self._db.scalar(
            select(Partner).where(
                Partner.id == command.partner_id,
                Partner.company_id == command.company_id,
            )
        )
        if partner is None:
            raise ValueError("Partner not found for this company.")

        if partner.currency and partner.currency != command.currency:
            raise ValueError(
                f"Partner currency '{partner.currency}' does not match credit note currency '{command.currency}'."
            )

        if command.note_type == "customer_credit_note" and not partner.is_customer:
            raise ValueError("The selected partner is not marked as a customer.")
        if command.note_type == "vendor_debit_note" and not partner.is_vendor:
            raise ValueError("The selected partner is not marked as a vendor.")

        # Check existing credit_note_no
        existing = self._db.scalar(
            select(CreditNote).where(
                CreditNote.company_id == command.company_id,
                CreditNote.note_type == command.note_type,
                CreditNote.credit_note_no == command.credit_note_no.strip(),
            )
        )
        if existing:
            raise ValueError(
                f"A document with number '{command.credit_note_no}' already exists for this type."
            )

        subtotal = Decimal("0.00")
        lines: list[CreditNoteLine] = []
        for index, item in enumerate(command.lines, start=1):
            if item.quantity <= Decimal("0.00"):
                raise ValueError("Line quantity must be greater than zero.")
            if item.unit_price < Decimal("0.00"):
                raise ValueError("Line unit price cannot be negative.")

            account = self._db.scalar(
                select(Account).where(
                    Account.id == item.account_id,
                    Account.company_id == command.company_id,
                )
            )
            if account is None:
                raise ValueError(f"Account {item.account_id} not found for this company.")
            if account.currency != command.currency:
                raise ValueError(
                    f"Line account '{account.name}' currency '{account.currency}' does not match document currency '{command.currency}'."
                )

            line_subtotal = item.quantity * item.unit_price
            subtotal += line_subtotal
            lines.append(
                CreditNoteLine(
                    line_no=index,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=line_subtotal,
                    account_id=item.account_id,
                )
            )

        tax_amount = command.tax_amount or Decimal("0.00")
        total_amount = subtotal + tax_amount

        # Validate allocations
        total_allocated = sum((a.amount for a in command.allocations), Decimal("0.00"))
        if total_allocated > total_amount:
            raise ValueError(
                f"Total allocated amount ({total_allocated}) cannot exceed document total ({total_amount})."
            )

        allocations: list[CreditNoteAllocation] = []
        for alloc_cmd in command.allocations:
            if alloc_cmd.amount <= Decimal("0.00"):
                raise ValueError("Allocation amount must be greater than zero.")

            invoice = self._db.scalar(
                select(Invoice)
                .options(
                    selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
                    selectinload(Invoice.credit_allocations).selectinload(CreditNoteAllocation.credit_note),
                )
                .where(Invoice.id == alloc_cmd.invoice_id)
            )
            if invoice is None:
                raise ValueError(f"Invoice {alloc_cmd.invoice_id} not found.")

            if invoice.company_id != command.company_id:
                raise ValueError(f"Invoice {invoice.invoice_no} belongs to another company.")
            if invoice.partner_id != command.partner_id:
                raise ValueError(f"Invoice {invoice.invoice_no} does not belong to the selected partner.")
            if invoice.currency != command.currency:
                raise ValueError(
                    f"Invoice {invoice.invoice_no} currency '{invoice.currency}' does not match document currency '{command.currency}'."
                )
            if invoice.status in ("draft", "void", "cancelled"):
                raise ValueError(
                    f"Cannot allocate credit to invoice {invoice.invoice_no} in status '{invoice.status}'."
                )
            if alloc_cmd.amount > invoice.residual_amount:
                raise ValueError(
                    f"Allocation amount ({alloc_cmd.amount}) exceeds invoice {invoice.invoice_no} remaining balance ({invoice.residual_amount})."
                )

            allocations.append(
                CreditNoteAllocation(
                    company_id=command.company_id,
                    invoice_id=invoice.id,
                    amount=alloc_cmd.amount,
                )
            )

        credit_note = CreditNote(
            company_id=command.company_id,
            partner_id=command.partner_id,
            note_type=command.note_type,
            credit_note_no=command.credit_note_no.strip(),
            reference=command.reference,
            issue_date=command.issue_date,
            currency=command.currency,
            status="draft",
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            reason=command.reason,
            created_by_user_id=command.created_by_user_id,
            lines=lines,
            allocations=allocations,
        )

        self._db.add(credit_note)
        flush_or_rollback(self._db)
        self._db.refresh(
            credit_note,
            ["partner", "lines", "allocations"],
        )
        return self._to_dto(credit_note)

    def get_by_id(self, credit_note_id: int) -> CreditNoteDTO | None:
        statement = (
            select(CreditNote)
            .options(
                selectinload(CreditNote.partner),
                selectinload(CreditNote.lines).selectinload(CreditNoteLine.account),
                selectinload(CreditNote.allocations).selectinload(CreditNoteAllocation.invoice),
            )
            .where(CreditNote.id == credit_note_id)
        )
        cn = self._db.scalar(statement)
        return self._to_dto(cn) if cn else None

    def get_by_no(
        self,
        company_id: int,
        note_type: str,
        credit_note_no: str,
    ) -> CreditNoteDTO | None:
        statement = (
            select(CreditNote)
            .options(
                selectinload(CreditNote.partner),
                selectinload(CreditNote.lines).selectinload(CreditNoteLine.account),
                selectinload(CreditNote.allocations).selectinload(CreditNoteAllocation.invoice),
            )
            .where(
                CreditNote.company_id == company_id,
                CreditNote.note_type == note_type,
                CreditNote.credit_note_no == credit_note_no.strip(),
            )
        )
        cn = self._db.scalar(statement)
        return self._to_dto(cn) if cn else None

    def list(self, query: CreditNoteQuery) -> CreditNotePageDTO:
        statement = select(CreditNote).where(CreditNote.company_id == query.company_id)

        if query.note_type is not None:
            statement = statement.where(CreditNote.note_type == query.note_type)
        if query.partner_id is not None:
            statement = statement.where(CreditNote.partner_id == query.partner_id)
        if query.status is not None:
            statement = statement.where(CreditNote.status == query.status)
        if query.currency is not None:
            statement = statement.where(CreditNote.currency == query.currency)
        if query.start_date is not None:
            statement = statement.where(CreditNote.issue_date >= query.start_date)
        if query.end_date is not None:
            statement = statement.where(CreditNote.issue_date <= query.end_date)
        if query.search:
            pattern = f"%{query.search.strip()}%"
            statement = statement.where(
                or_(
                    CreditNote.credit_note_no.ilike(pattern),
                    CreditNote.reference.ilike(pattern),
                    CreditNote.reason.ilike(pattern),
                )
            )

        total = self._db.scalar(
            select(func.count()).select_from(statement.subquery())
        ) or 0

        statement = (
            statement.options(
                selectinload(CreditNote.partner),
                selectinload(CreditNote.lines).selectinload(CreditNoteLine.account),
                selectinload(CreditNote.allocations).selectinload(CreditNoteAllocation.invoice),
            )
            .order_by(CreditNote.issue_date.desc(), CreditNote.id.desc())
            .offset(query.skip)
            .limit(query.limit)
        )
        items = self._db.scalars(statement).all()

        return CreditNotePageDTO(
            items=[self._to_dto(cn) for cn in items],
            total=total,
            skip=query.skip,
            limit=query.limit,
        )

    def post(self, command: PostCreditNoteCommand) -> CreditNoteDTO:
        cn = self._db.scalar(
            select(CreditNote)
            .options(
                selectinload(CreditNote.partner),
                selectinload(CreditNote.lines).selectinload(CreditNoteLine.account),
                selectinload(CreditNote.allocations).selectinload(CreditNoteAllocation.invoice),
            )
            .where(CreditNote.id == command.credit_note_id)
        )
        if cn is None:
            raise ValueError(f"Document {command.credit_note_id} not found.")

        if cn.status != "draft":
            raise ValueError(f"Cannot post document in status '{cn.status}'. Must be 'draft'.")

        if not cn.lines:
            raise ValueError("Cannot post a document with no line items.")

        # Validate target account (AR or AP)
        target_account = self._db.scalar(
            select(Account).where(
                Account.id == command.receivable_or_payable_account_id,
                Account.company_id == cn.company_id,
            )
        )
        if target_account is None:
            raise ValueError("Target receivable/payable account not found for this company.")
        if target_account.currency != cn.currency:
            raise ValueError(
                f"Account '{target_account.name}' has currency '{target_account.currency}', "
                f"which does not match document currency '{cn.currency}'."
            )

        # Validate line accounts
        for line in cn.lines:
            if line.account.currency != cn.currency:
                raise ValueError(
                    f"Line account '{line.account.name}' currency '{line.account.currency}' "
                    f"does not match document currency '{cn.currency}'."
                )

        # Validate partner currency
        if cn.partner.currency and cn.partner.currency != cn.currency:
            raise ValueError(
                f"Partner currency '{cn.partner.currency}' does not match document currency '{cn.currency}'."
            )

        # Re-validate allocations against invoices
        for alloc in cn.allocations:
            invoice = self._db.scalar(
                select(Invoice)
                .options(
                    selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
                    selectinload(Invoice.credit_allocations).selectinload(CreditNoteAllocation.credit_note),
                )
                .where(Invoice.id == alloc.invoice_id)
            )
            if invoice is None:
                raise ValueError(f"Invoice {alloc.invoice_id} not found.")
            if invoice.currency != cn.currency:
                raise ValueError(
                    f"Invoice {invoice.invoice_no} currency '{invoice.currency}' does not match document currency '{cn.currency}'."
                )
            if invoice.status in ("draft", "void", "cancelled"):
                raise ValueError(
                    f"Cannot allocate credit to invoice {invoice.invoice_no} in status '{invoice.status}'."
                )

            # Available residual excluding this credit note's allocation
            existing_settled = (
                sum(
                    (
                        a.amount
                        for a in invoice.allocations
                        if a.payment and a.payment.status == "posted"
                    ),
                    Decimal("0.00"),
                )
                + sum(
                    (
                        ca.amount
                        for ca in invoice.credit_allocations
                        if ca.credit_note
                        and ca.credit_note.status == "posted"
                        and ca.credit_note_id != cn.id
                    ),
                    Decimal("0.00"),
                )
            )
            available_residual = invoice.total_amount - existing_settled
            if alloc.amount > available_residual:
                raise ValueError(
                    f"Allocation amount ({alloc.amount}) exceeds invoice {invoice.invoice_no} remaining balance ({available_residual})."
                )

        # Generate Journal Entry
        entry_prefix = "CCN" if cn.note_type == "customer_credit_note" else "VDN"
        entry_no = f"{entry_prefix}-{cn.credit_note_no}"

        journal_lines: list[JournalLine] = []
        partner_name = cn.partner.name if cn.partner else ""
        ref_text = f" ({cn.reference})" if cn.reference else ""

        if cn.note_type == "customer_credit_note":
            # Customer Credit Note:
            # Debit Revenue/Sales Returns accounts (line.subtotal)
            # Credit Accounts Receivable (cn.total_amount)
            for idx, line in enumerate(cn.lines, start=1):
                journal_lines.append(
                    JournalLine(
                        company_id=cn.company_id,
                        account_id=line.account_id,
                        line_no=idx,
                        debit=line.subtotal,
                        credit=Decimal("0.00"),
                        description=f"Credit Note {cn.credit_note_no} - {line.description}",
                    )
                )
            journal_lines.append(
                JournalLine(
                    company_id=cn.company_id,
                    account_id=command.receivable_or_payable_account_id,
                    line_no=len(cn.lines) + 1,
                    debit=Decimal("0.00"),
                    credit=cn.total_amount,
                    description=f"Credit Note {cn.credit_note_no}{ref_text} - {partner_name}",
                )
            )
        else:
            # Vendor Debit Note:
            # Debit Accounts Payable (cn.total_amount)
            # Credit Purchase Returns / Expense accounts (line.subtotal)
            journal_lines.append(
                JournalLine(
                    company_id=cn.company_id,
                    account_id=command.receivable_or_payable_account_id,
                    line_no=1,
                    debit=cn.total_amount,
                    credit=Decimal("0.00"),
                    description=f"Debit Note {cn.credit_note_no}{ref_text} - {partner_name}",
                )
            )
            for idx, line in enumerate(cn.lines, start=2):
                journal_lines.append(
                    JournalLine(
                        company_id=cn.company_id,
                        account_id=line.account_id,
                        line_no=idx,
                        debit=Decimal("0.00"),
                        credit=line.subtotal,
                        description=f"Debit Note {cn.credit_note_no} - {line.description}",
                    )
                )

        now = datetime.now(timezone.utc)
        journal_entry = JournalEntry(
            company_id=cn.company_id,
            fiscal_year_id=command.fiscal_year_id,
            fiscal_period_id=command.fiscal_period_id,
            entry_no=entry_no,
            entry_date=cn.issue_date,
            description=f"{entry_prefix} {cn.credit_note_no}: {cn.reason or ''}".strip(),
            status="posted",
            source_type=cn.note_type,
            source_id=str(cn.id),
            created_by_user_id=command.posted_by_user_id,
            posted_at=now,
            lines=journal_lines,
        )

        self._db.add(journal_entry)
        flush_or_rollback(self._db)

        cn.journal_entry_id = journal_entry.id
        cn.status = "posted"

        # Update allocated invoices status if fully settled
        for alloc in cn.allocations:
            invoice = self._db.scalar(
                select(Invoice)
                .execution_options(populate_existing=True)
                .options(
                    selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
                    selectinload(Invoice.credit_allocations).selectinload(CreditNoteAllocation.credit_note),
                )
                .where(Invoice.id == alloc.invoice_id)
            )
            if invoice:
                settled_sum = (
                    sum(
                        (
                            a.amount
                            for a in invoice.allocations
                            if a.payment and a.payment.status == "posted"
                        ),
                        Decimal("0.00"),
                    )
                    + sum(
                        (
                            ca.amount
                            for ca in invoice.credit_allocations
                            if ca.credit_note_id == cn.id
                            or (ca.credit_note and ca.credit_note.status == "posted")
                        ),
                        Decimal("0.00"),
                    )
                )
                if settled_sum >= invoice.total_amount:
                    invoice.status = "paid"

        flush_or_rollback(self._db)
        return self._to_dto(cn)

    def void(self, command: VoidCreditNoteCommand) -> CreditNoteDTO:
        cn = self._db.scalar(
            select(CreditNote)
            .options(
                selectinload(CreditNote.partner),
                selectinload(CreditNote.lines).selectinload(CreditNoteLine.account),
                selectinload(CreditNote.allocations).selectinload(CreditNoteAllocation.invoice),
            )
            .where(CreditNote.id == command.credit_note_id)
        )
        if cn is None:
            raise ValueError(f"Document {command.credit_note_id} not found.")

        if cn.status == "void":
            return self._to_dto(cn)

        # Void linked JournalEntry
        if cn.journal_entry_id:
            journal_entry = self._db.scalar(
                select(JournalEntry).where(JournalEntry.id == cn.journal_entry_id)
            )
            if journal_entry and journal_entry.status != "void":
                journal_entry.status = "void"

        cn.status = "void"

        # Check and update allocated invoice statuses
        for alloc in cn.allocations:
            invoice = self._db.scalar(
                select(Invoice)
                .execution_options(populate_existing=True)
                .options(
                    selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
                    selectinload(Invoice.credit_allocations).selectinload(CreditNoteAllocation.credit_note),
                )
                .where(Invoice.id == alloc.invoice_id)
            )
            if invoice and invoice.status == "paid":
                settled_sum = (
                    sum(
                        (
                            a.amount
                            for a in invoice.allocations
                            if a.payment and a.payment.status == "posted"
                        ),
                        Decimal("0.00"),
                    )
                    + sum(
                        (
                            ca.amount
                            for ca in invoice.credit_allocations
                            if ca.credit_note_id != cn.id
                            and ca.credit_note
                            and ca.credit_note.status == "posted"
                        ),
                        Decimal("0.00"),
                    )
                )
                if settled_sum < invoice.total_amount:
                    invoice.status = "posted"

        flush_or_rollback(self._db)
        return self._to_dto(cn)

    def allocate(self, command: AllocateCreditNoteCommand) -> CreditNoteDTO:
        cn = self._db.scalar(
            select(CreditNote)
            .options(
                selectinload(CreditNote.partner),
                selectinload(CreditNote.lines).selectinload(CreditNoteLine.account),
                selectinload(CreditNote.allocations).selectinload(CreditNoteAllocation.invoice),
            )
            .where(CreditNote.id == command.credit_note_id)
        )
        if cn is None:
            raise ValueError(f"Document {command.credit_note_id} not found.")

        if cn.status != "posted":
            raise ValueError("Only posted credit notes can be allocated.")

        # Check total allocation amount
        new_total_allocated = sum((a.amount for a in command.allocations), Decimal("0.00"))
        if new_total_allocated > cn.total_amount:
            raise ValueError(
                f"Total allocated amount ({new_total_allocated}) cannot exceed document total ({cn.total_amount})."
            )

        # Clear existing allocations and set new ones
        cn.allocations.clear()
        flush_or_rollback(self._db)

        for alloc_cmd in command.allocations:
            if alloc_cmd.amount <= Decimal("0.00"):
                raise ValueError("Allocation amount must be greater than zero.")

            invoice = self._db.scalar(
                select(Invoice)
                .options(
                    selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
                    selectinload(Invoice.credit_allocations).selectinload(CreditNoteAllocation.credit_note),
                )
                .where(Invoice.id == alloc_cmd.invoice_id)
            )
            if invoice is None:
                raise ValueError(f"Invoice {alloc_cmd.invoice_id} not found.")
            if invoice.company_id != cn.company_id:
                raise ValueError(f"Invoice {invoice.invoice_no} belongs to another company.")
            if invoice.partner_id != cn.partner_id:
                raise ValueError(f"Invoice {invoice.invoice_no} does not belong to the selected partner.")
            if invoice.currency != cn.currency:
                raise ValueError(
                    f"Invoice {invoice.invoice_no} currency '{invoice.currency}' does not match document currency '{cn.currency}'."
                )
            if invoice.status in ("draft", "void", "cancelled"):
                raise ValueError(
                    f"Cannot allocate credit to invoice {invoice.invoice_no} in status '{invoice.status}'."
                )

            existing_settled = (
                sum(
                    (
                        a.amount
                        for a in invoice.allocations
                        if a.payment and a.payment.status == "posted"
                    ),
                    Decimal("0.00"),
                )
                + sum(
                    (
                        ca.amount
                        for ca in invoice.credit_allocations
                        if ca.credit_note
                        and ca.credit_note.status == "posted"
                        and ca.credit_note_id != cn.id
                    ),
                    Decimal("0.00"),
                )
            )
            available_residual = invoice.total_amount - existing_settled
            if alloc_cmd.amount > available_residual:
                raise ValueError(
                    f"Allocation amount ({alloc_cmd.amount}) exceeds remaining balance ({available_residual})."
                )

            cn.allocations.append(
                CreditNoteAllocation(
                    company_id=cn.company_id,
                    credit_note_id=cn.id,
                    invoice_id=invoice.id,
                    amount=alloc_cmd.amount,
                )
            )

        # Update allocated invoices status if fully settled
        for alloc in cn.allocations:
            invoice = self._db.scalar(
                select(Invoice)
                .execution_options(populate_existing=True)
                .options(
                    selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
                    selectinload(Invoice.credit_allocations).selectinload(CreditNoteAllocation.credit_note),
                )
                .where(Invoice.id == alloc.invoice_id)
            )
            if invoice:
                settled_sum = (
                    sum(
                        (
                            a.amount
                            for a in invoice.allocations
                            if a.payment and a.payment.status == "posted"
                        ),
                        Decimal("0.00"),
                    )
                    + sum(
                        (
                            ca.amount
                            for ca in invoice.credit_allocations
                            if ca.credit_note_id == cn.id
                            or (ca.credit_note and ca.credit_note.status == "posted")
                        ),
                        Decimal("0.00"),
                    )
                )
                if settled_sum >= invoice.total_amount:
                    invoice.status = "paid"
                elif invoice.status == "paid":
                    invoice.status = "posted"

        flush_or_rollback(self._db)
        self._db.refresh(cn, ["allocations"])
        return self._to_dto(cn)
