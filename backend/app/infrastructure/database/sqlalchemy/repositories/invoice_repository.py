from __future__ import annotations

"""SQLAlchemy adapter for invoice persistence and GL posting."""

from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.application.invoices.dto import (
    CreateInvoiceCommand,
    InvoiceDTO,
    InvoiceLineDTO,
    InvoicePageDTO,
    InvoiceQuery,
    PostInvoiceCommand,
    UpdateInvoiceCommand,
    VoidInvoiceCommand,
)
from app.application.invoices.ports import InvoiceRepository
from app.core.database import flush_or_rollback
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.credit_note import CreditNoteAllocation
from app.modules.accounting.models.invoice import Invoice, InvoiceLine
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.partner import Partner
from app.modules.accounting.models.payment import PaymentAllocation


class SqlAlchemyInvoiceRepository(InvoiceRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _line_to_dto(line: InvoiceLine) -> InvoiceLineDTO:
        return InvoiceLineDTO(
            id=line.id,
            invoice_id=line.invoice_id,
            line_no=line.line_no,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            subtotal=line.subtotal,
            account_id=line.account_id,
        )

    @classmethod
    def _to_dto(cls, invoice: Invoice) -> InvoiceDTO:
        partner_name = invoice.partner.name if invoice.partner else None
        return InvoiceDTO(
            id=invoice.id,
            company_id=invoice.company_id,
            partner_id=invoice.partner_id,
            invoice_type=invoice.invoice_type,
            invoice_no=invoice.invoice_no,
            reference=invoice.reference,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            currency=invoice.currency,
            status=invoice.status,
            subtotal=invoice.subtotal,
            tax_amount=invoice.tax_amount,
            total_amount=invoice.total_amount,
            paid_amount=invoice.paid_amount,
            credited_amount=invoice.credited_amount,
            residual_amount=invoice.residual_amount,
            payment_status=invoice.payment_status,
            journal_entry_id=invoice.journal_entry_id,
            notes=invoice.notes,
            created_by_user_id=invoice.created_by_user_id,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
            partner_name=partner_name,
            lines=[cls._line_to_dto(line) for line in invoice.lines],
        )

    def create(self, command: CreateInvoiceCommand) -> InvoiceDTO:
        if not command.lines:
            raise ValueError("An invoice must contain at least one line item.")

        subtotal = Decimal("0.00")
        lines = []
        for index, item in enumerate(command.lines, start=1):
            line_subtotal = item.quantity * item.unit_price
            subtotal += line_subtotal
            lines.append(
                InvoiceLine(
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

        invoice = Invoice(
            company_id=command.company_id,
            partner_id=command.partner_id,
            invoice_type=command.invoice_type,
            invoice_no=command.invoice_no,
            reference=command.reference,
            issue_date=command.issue_date,
            due_date=command.due_date,
            currency=command.currency,
            status="draft",
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            notes=command.notes,
            created_by_user_id=command.created_by_user_id,
            lines=lines,
        )

        self._db.add(invoice)
        flush_or_rollback(self._db)
        # Ensure relationships are loaded
        self._db.refresh(invoice, ["partner", "lines"])
        return self._to_dto(invoice)

    def update(self, command: UpdateInvoiceCommand) -> InvoiceDTO:
        invoice = self._db.scalar(
            select(Invoice)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.partner),
                selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
            )
            .where(Invoice.id == command.invoice_id)
        )
        if invoice is None:
            raise ValueError(f"Invoice {command.invoice_id} not found")

        if invoice.status != "draft":
            raise ValueError("Only draft invoices can be modified.")

        for field in ("partner_id", "reference", "issue_date", "due_date", "notes"):
            if field in command.fields:
                setattr(invoice, field, getattr(command, field))

        if "tax_amount" in command.fields and command.tax_amount is not None:
            invoice.tax_amount = command.tax_amount

        if "lines" in command.fields and command.lines is not None:
            invoice.lines.clear()
            subtotal = Decimal("0.00")
            for index, item in enumerate(command.lines, start=1):
                line_subtotal = item.quantity * item.unit_price
                subtotal += line_subtotal
                invoice.lines.append(
                    InvoiceLine(
                        line_no=index,
                        description=item.description,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        subtotal=line_subtotal,
                        account_id=item.account_id,
                    )
                )
            invoice.subtotal = subtotal

        invoice.total_amount = invoice.subtotal + invoice.tax_amount

        flush_or_rollback(self._db)
        return self._to_dto(invoice)

    def get_by_id(self, invoice_id: int) -> InvoiceDTO | None:
        invoice = self._db.scalar(
            select(Invoice)
            .execution_options(populate_existing=True)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.partner),
                selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
                selectinload(Invoice.credit_allocations).selectinload(CreditNoteAllocation.credit_note),
            )
            .where(Invoice.id == invoice_id)
        )
        return self._to_dto(invoice) if invoice else None

    def get_by_no(
        self,
        company_id: int,
        invoice_type: str,
        invoice_no: str,
    ) -> InvoiceDTO | None:
        invoice = self._db.scalar(
            select(Invoice)
            .execution_options(populate_existing=True)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.partner),
                selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
                selectinload(Invoice.credit_allocations).selectinload(CreditNoteAllocation.credit_note),
            )
            .where(
                Invoice.company_id == company_id,
                Invoice.invoice_type == invoice_type,
                Invoice.invoice_no == invoice_no,
            )
        )
        return self._to_dto(invoice) if invoice else None

    def list(self, query: InvoiceQuery) -> InvoicePageDTO:
        statement = select(Invoice).where(Invoice.company_id == query.company_id)

        if query.invoice_type is not None:
            statement = statement.where(Invoice.invoice_type == query.invoice_type)

        if query.partner_id is not None:
            statement = statement.where(Invoice.partner_id == query.partner_id)

        if query.status is not None:
            statement = statement.where(Invoice.status == query.status)

        if query.currency is not None:
            statement = statement.where(Invoice.currency == query.currency)

        if query.start_date is not None:
            statement = statement.where(Invoice.issue_date >= query.start_date)

        if query.end_date is not None:
            statement = statement.where(Invoice.issue_date <= query.end_date)

        if query.search:
            pattern = f"%{query.search.strip()}%"
            statement = statement.where(
                or_(
                    Invoice.invoice_no.ilike(pattern),
                    Invoice.reference.ilike(pattern),
                )
            )

        total = self._db.scalar(
            select(func.count()).select_from(statement.subquery())
        ) or 0

        statement = (
            statement.execution_options(populate_existing=True)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.partner),
                selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
                selectinload(Invoice.credit_allocations).selectinload(CreditNoteAllocation.credit_note),
            )
            .order_by(Invoice.issue_date.desc(), Invoice.id.desc())
            .offset(query.skip)
            .limit(query.limit)
        )
        invoices = self._db.scalars(statement).all()

        return InvoicePageDTO(
            items=[self._to_dto(inv) for inv in invoices],
            total=total,
            skip=query.skip,
            limit=query.limit,
        )

    def post(self, command: PostInvoiceCommand) -> InvoiceDTO:
        invoice = self._db.scalar(
            select(Invoice)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.partner),
                selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
            )
            .where(Invoice.id == command.invoice_id)
        )
        if invoice is None:
            raise ValueError(f"Invoice {command.invoice_id} not found")

        if invoice.status != "draft":
            raise ValueError(f"Cannot post invoice in status '{invoice.status}'. Must be 'draft'.")

        if not invoice.lines:
            raise ValueError("Cannot post an invoice with no line items.")

        # Check account currencies against invoice currency
        target_account = self._db.scalar(
            select(Account).where(Account.id == command.receivable_or_payable_account_id)
        )
        if target_account is None:
            raise ValueError("Target receivable/payable account not found.")

        if target_account.currency != invoice.currency:
            raise ValueError(
                f"Account '{target_account.name}' has currency '{target_account.currency}', "
                f"which does not match invoice currency '{invoice.currency}'."
            )

        for line in invoice.lines:
            line_account = self._db.scalar(select(Account).where(Account.id == line.account_id))
            if line_account is None:
                raise ValueError(f"Line account {line.account_id} not found.")
            if line_account.currency != invoice.currency:
                raise ValueError(
                    f"Line account '{line_account.name}' currency '{line_account.currency}' "
                    f"does not match invoice currency '{invoice.currency}'."
                )

        # Generate Journal Entry
        entry_prefix = "INV" if invoice.invoice_type == "out_invoice" else "BILL"
        entry_no = f"{entry_prefix}-{invoice.invoice_no}"

        journal_lines: list[JournalLine] = []
        now = datetime.now(timezone.utc)

        if invoice.invoice_type == "out_invoice":
            # Sales Invoice:
            # Line 1: Debit Accounts Receivable (total_amount)
            journal_lines.append(
                JournalLine(
                    company_id=invoice.company_id,
                    account_id=command.receivable_or_payable_account_id,
                    line_no=1,
                    debit=invoice.total_amount,
                    credit=Decimal("0.00"),
                    description=f"Sales invoice {invoice.invoice_no} - {invoice.partner.name if invoice.partner else ''}",
                )
            )
            # Lines 2..N: Credit Revenue accounts (line.subtotal)
            for idx, line in enumerate(invoice.lines, start=2):
                journal_lines.append(
                    JournalLine(
                        company_id=invoice.company_id,
                        account_id=line.account_id,
                        line_no=idx,
                        debit=Decimal("0.00"),
                        credit=line.subtotal,
                        description=line.description,
                    )
                )
        else:
            # Purchase Bill:
            # Lines 1..N: Debit Expense/Asset accounts (line.subtotal)
            for idx, line in enumerate(invoice.lines, start=1):
                journal_lines.append(
                    JournalLine(
                        company_id=invoice.company_id,
                        account_id=line.account_id,
                        line_no=idx,
                        debit=line.subtotal,
                        credit=Decimal("0.00"),
                        description=line.description,
                    )
                )
            # Last Line: Credit Accounts Payable (total_amount)
            journal_lines.append(
                JournalLine(
                    company_id=invoice.company_id,
                    account_id=command.receivable_or_payable_account_id,
                    line_no=len(invoice.lines) + 1,
                    debit=Decimal("0.00"),
                    credit=invoice.total_amount,
                    description=f"Purchase bill {invoice.invoice_no} - {invoice.partner.name if invoice.partner else ''}",
                )
            )

        journal_entry = JournalEntry(
            company_id=invoice.company_id,
            fiscal_year_id=command.fiscal_year_id,
            fiscal_period_id=command.fiscal_period_id,
            entry_no=entry_no,
            entry_date=invoice.issue_date,
            description=f"{entry_prefix} #{invoice.invoice_no}: {invoice.notes or ''}".strip(),
            status="posted",
            source_type=invoice.invoice_type,
            source_id=str(invoice.id),
            created_by_user_id=command.posted_by_user_id,
            posted_at=now,
            lines=journal_lines,
        )

        self._db.add(journal_entry)
        flush_or_rollback(self._db)

        invoice.journal_entry_id = journal_entry.id
        invoice.status = "posted"
        flush_or_rollback(self._db)

        return self._to_dto(invoice)

    def void(self, command: VoidInvoiceCommand) -> InvoiceDTO:
        invoice = self._db.scalar(
            select(Invoice)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.partner),
                selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
            )
            .where(Invoice.id == command.invoice_id)
        )
        if invoice is None:
            raise ValueError(f"Invoice {command.invoice_id} not found")

        if invoice.status == "paid":
            raise ValueError("Cannot void a paid invoice.")

        if invoice.status == "void":
            return self._to_dto(invoice)

        if invoice.journal_entry_id:
            journal_entry = self._db.scalar(
                select(JournalEntry).where(JournalEntry.id == invoice.journal_entry_id)
            )
            if journal_entry and journal_entry.status != "void":
                journal_entry.status = "void"

        invoice.status = "void"
        flush_or_rollback(self._db)
        return self._to_dto(invoice)

    def get_open_invoices(
        self,
        company_id: int,
        partner_id: int,
        currency: str | None = None,
    ) -> list[InvoiceDTO]:
        statement = (
            select(Invoice)
            .where(
                Invoice.company_id == company_id,
                Invoice.partner_id == partner_id,
                Invoice.status.in_(("posted", "paid")),
            )
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.partner),
                selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment),
                selectinload(Invoice.credit_allocations).selectinload(CreditNoteAllocation.credit_note),
            )
            .order_by(Invoice.issue_date.asc(), Invoice.id.asc())
        )
        if currency is not None:
            statement = statement.where(Invoice.currency == currency.upper())

        invoices = self._db.scalars(statement).all()
        return [
            self._to_dto(inv)
            for inv in invoices
            if inv.residual_amount > Decimal("0.00")
        ]
