from __future__ import annotations

"""SQLAlchemy adapter for payment persistence, allocations, and GL posting."""

from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.application.payments.dto import (
    CreatePaymentAllocationCommand,
    CreatePaymentCommand,
    PaymentAllocationDTO,
    PaymentDTO,
    PaymentPageDTO,
    PaymentQuery,
    PostPaymentCommand,
    VoidPaymentCommand,
)
from app.application.payments.ports import PaymentRepository
from app.core.database import flush_or_rollback
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.invoice import Invoice
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.partner import Partner
from app.modules.accounting.models.payment import Payment, PaymentAllocation


class SqlAlchemyPaymentRepository(PaymentRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _allocation_to_dto(alloc: PaymentAllocation) -> PaymentAllocationDTO:
        invoice_no = alloc.invoice.invoice_no if alloc.invoice else None
        return PaymentAllocationDTO(
            id=alloc.id,
            company_id=alloc.company_id,
            payment_id=alloc.payment_id,
            invoice_id=alloc.invoice_id,
            amount=alloc.amount,
            created_at=alloc.created_at,
            invoice_no=invoice_no,
        )

    @classmethod
    def _to_dto(cls, payment: Payment) -> PaymentDTO:
        partner_name = payment.partner.name if payment.partner else None
        bank_name = (
            payment.bank_or_cash_account.name
            if payment.bank_or_cash_account
            else None
        )
        ar_ap_name = (
            payment.receivable_or_payable_account.name
            if payment.receivable_or_payable_account
            else None
        )
        allocations_dto = [cls._allocation_to_dto(a) for a in payment.allocations]
        allocated_amount = sum((a.amount for a in payment.allocations), Decimal("0.00"))
        unallocated_amount = max(Decimal("0.00"), payment.amount - allocated_amount)

        return PaymentDTO(
            id=payment.id,
            company_id=payment.company_id,
            partner_id=payment.partner_id,
            payment_type=payment.payment_type,
            currency_code=payment.currency_code,
            amount=payment.amount,
            payment_date=payment.payment_date,
            bank_or_cash_account_id=payment.bank_or_cash_account_id,
            receivable_or_payable_account_id=payment.receivable_or_payable_account_id,
            status=payment.status,
            reference=payment.reference,
            memo=payment.memo,
            journal_entry_id=payment.journal_entry_id,
            created_by_user_id=payment.created_by_user_id,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            partner_name=partner_name,
            bank_account_name=bank_name,
            receivable_or_payable_account_name=ar_ap_name,
            allocations=allocations_dto,
            allocated_amount=allocated_amount,
            unallocated_amount=unallocated_amount,
        )

    def create(self, command: CreatePaymentCommand) -> PaymentDTO:
        if command.amount <= Decimal("0.00"):
            raise ValueError("Payment amount must be greater than zero.")

        partner = self._db.scalar(
            select(Partner).where(
                Partner.id == command.partner_id,
                Partner.company_id == command.company_id,
            )
        )
        if partner is None:
            raise ValueError("Partner not found for this company.")

        if partner.currency and partner.currency != command.currency_code:
            raise ValueError(
                f"Partner currency '{partner.currency}' does not match payment currency '{command.currency_code}'."
            )

        if command.payment_type == "customer_receipt" and not partner.is_customer:
            raise ValueError("The selected partner is not marked as a customer.")
        if command.payment_type == "vendor_payment" and not partner.is_vendor:
            raise ValueError("The selected partner is not marked as a vendor.")

        bank_account = self._db.scalar(
            select(Account).where(
                Account.id == command.bank_or_cash_account_id,
                Account.company_id == command.company_id,
            )
        )
        if bank_account is None:
            raise ValueError("Bank/Cash account not found for this company.")
        if bank_account.currency != command.currency_code:
            raise ValueError(
                f"Bank/Cash account currency '{bank_account.currency}' does not match payment currency '{command.currency_code}'."
            )

        ar_ap_account = self._db.scalar(
            select(Account).where(
                Account.id == command.receivable_or_payable_account_id,
                Account.company_id == command.company_id,
            )
        )
        if ar_ap_account is None:
            raise ValueError("Receivable/Payable account not found for this company.")
        if ar_ap_account.currency != command.currency_code:
            raise ValueError(
                f"Receivable/Payable account currency '{ar_ap_account.currency}' does not match payment currency '{command.currency_code}'."
            )

        # Validate allocations
        total_allocated = sum((a.amount for a in command.allocations), Decimal("0.00"))
        if total_allocated > command.amount:
            raise ValueError(
                f"Total allocated amount ({total_allocated}) cannot exceed payment amount ({command.amount})."
            )

        allocations: list[PaymentAllocation] = []
        for alloc_cmd in command.allocations:
            if alloc_cmd.amount <= Decimal("0.00"):
                raise ValueError("Allocation amount must be greater than zero.")

            invoice = self._db.scalar(
                select(Invoice)
                .options(
                    selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment)
                )
                .where(Invoice.id == alloc_cmd.invoice_id)
            )
            if invoice is None:
                raise ValueError(f"Invoice {alloc_cmd.invoice_id} not found.")

            if invoice.company_id != command.company_id:
                raise ValueError(
                    f"Invoice {invoice.invoice_no} belongs to another company."
                )

            if invoice.partner_id != command.partner_id:
                raise ValueError(
                    f"Invoice {invoice.invoice_no} does not belong to the selected partner."
                )

            if invoice.currency != command.currency_code:
                raise ValueError(
                    f"Invoice {invoice.invoice_no} currency '{invoice.currency}' does not match payment currency '{command.currency_code}'."
                )

            if invoice.status in ("draft", "void", "cancelled"):
                raise ValueError(
                    f"Cannot allocate payment to invoice {invoice.invoice_no} in status '{invoice.status}'."
                )

            if alloc_cmd.amount > invoice.residual_amount:
                raise ValueError(
                    f"Allocation amount ({alloc_cmd.amount}) exceeds invoice {invoice.invoice_no} remaining balance ({invoice.residual_amount})."
                )

            allocations.append(
                PaymentAllocation(
                    company_id=command.company_id,
                    invoice_id=invoice.id,
                    amount=alloc_cmd.amount,
                )
            )

        payment = Payment(
            company_id=command.company_id,
            partner_id=command.partner_id,
            payment_type=command.payment_type,
            currency_code=command.currency_code,
            amount=command.amount,
            payment_date=command.payment_date,
            reference=command.reference,
            memo=command.memo,
            bank_or_cash_account_id=command.bank_or_cash_account_id,
            receivable_or_payable_account_id=command.receivable_or_payable_account_id,
            status="draft",
            created_by_user_id=command.created_by_user_id,
            allocations=allocations,
        )

        self._db.add(payment)
        flush_or_rollback(self._db)
        self._db.refresh(
            payment,
            [
                "partner",
                "bank_or_cash_account",
                "receivable_or_payable_account",
                "allocations",
            ],
        )
        return self._to_dto(payment)

    def get_by_id(self, payment_id: int) -> PaymentDTO | None:
        payment = self._db.scalar(
            select(Payment)
            .options(
                selectinload(Payment.partner),
                selectinload(Payment.bank_or_cash_account),
                selectinload(Payment.receivable_or_payable_account),
                selectinload(Payment.allocations).selectinload(PaymentAllocation.invoice),
            )
            .where(Payment.id == payment_id)
        )
        return self._to_dto(payment) if payment else None

    def list(self, query: PaymentQuery) -> PaymentPageDTO:
        statement = select(Payment).where(Payment.company_id == query.company_id)

        if query.payment_type is not None:
            statement = statement.where(Payment.payment_type == query.payment_type)

        if query.partner_id is not None:
            statement = statement.where(Payment.partner_id == query.partner_id)

        if query.status is not None:
            statement = statement.where(Payment.status == query.status)

        if query.currency is not None:
            statement = statement.where(Payment.currency_code == query.currency)

        if query.start_date is not None:
            statement = statement.where(Payment.payment_date >= query.start_date)

        if query.end_date is not None:
            statement = statement.where(Payment.payment_date <= query.end_date)

        if query.search:
            pattern = f"%{query.search.strip()}%"
            statement = statement.where(
                or_(
                    Payment.reference.ilike(pattern),
                    Payment.memo.ilike(pattern),
                )
            )

        total = self._db.scalar(
            select(func.count()).select_from(statement.subquery())
        ) or 0

        statement = (
            statement.options(
                selectinload(Payment.partner),
                selectinload(Payment.bank_or_cash_account),
                selectinload(Payment.receivable_or_payable_account),
                selectinload(Payment.allocations).selectinload(PaymentAllocation.invoice),
            )
            .order_by(Payment.payment_date.desc(), Payment.id.desc())
            .offset(query.skip)
            .limit(query.limit)
        )
        payments = self._db.scalars(statement).all()

        return PaymentPageDTO(
            items=[self._to_dto(p) for p in payments],
            total=total,
            skip=query.skip,
            limit=query.limit,
        )

    def post(self, command: PostPaymentCommand) -> PaymentDTO:
        payment = self._db.scalar(
            select(Payment)
            .options(
                selectinload(Payment.partner),
                selectinload(Payment.bank_or_cash_account),
                selectinload(Payment.receivable_or_payable_account),
                selectinload(Payment.allocations).selectinload(PaymentAllocation.invoice),
            )
            .where(Payment.id == command.payment_id)
        )
        if payment is None:
            raise ValueError(f"Payment {command.payment_id} not found.")

        if payment.status != "draft":
            raise ValueError(
                f"Cannot post payment in status '{payment.status}'. Must be 'draft'."
            )

        # Validate accounts & currency
        bank_account = payment.bank_or_cash_account
        if bank_account.currency != payment.currency_code:
            raise ValueError(
                f"Bank/Cash account currency '{bank_account.currency}' does not match payment currency '{payment.currency_code}'."
            )

        ar_ap_account = payment.receivable_or_payable_account
        if ar_ap_account.currency != payment.currency_code:
            raise ValueError(
                f"Receivable/Payable account currency '{ar_ap_account.currency}' does not match payment currency '{payment.currency_code}'."
            )

        # Re-check partner currency
        if payment.partner.currency and payment.partner.currency != payment.currency_code:
            raise ValueError(
                f"Partner currency '{payment.partner.currency}' does not match payment currency '{payment.currency_code}'."
            )

        # Re-validate allocations against invoices
        for alloc in payment.allocations:
            invoice = self._db.scalar(
                select(Invoice)
                .options(
                    selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment)
                )
                .where(Invoice.id == alloc.invoice_id)
            )
            if invoice is None:
                raise ValueError(f"Invoice {alloc.invoice_id} not found.")

            if invoice.currency != payment.currency_code:
                raise ValueError(
                    f"Invoice {invoice.invoice_no} currency '{invoice.currency}' does not match payment currency '{payment.currency_code}'."
                )

            if invoice.status in ("draft", "void", "cancelled"):
                raise ValueError(
                    f"Cannot allocate payment to invoice {invoice.invoice_no} in status '{invoice.status}'."
                )

            # When posting, the allocation amount must not exceed the invoice residual (excluding this payment's allocation)
            existing_paid = sum(
                (
                    a.amount
                    for a in invoice.allocations
                    if a.payment
                    and a.payment.status == "posted"
                    and a.payment_id != payment.id
                ),
                Decimal("0.00"),
            )
            available_residual = invoice.total_amount - existing_paid
            if alloc.amount > available_residual:
                raise ValueError(
                    f"Allocation amount ({alloc.amount}) exceeds invoice {invoice.invoice_no} remaining balance ({available_residual})."
                )

        # Generate Journal Entry
        entry_prefix = "REC" if payment.payment_type == "customer_receipt" else "PAY"
        entry_no = f"{entry_prefix}-{payment.id}"

        journal_lines: list[JournalLine] = []
        partner_name = payment.partner.name if payment.partner else ""
        ref_text = f" ({payment.reference})" if payment.reference else ""

        if payment.payment_type == "customer_receipt":
            # Debit Bank/Cash, Credit Accounts Receivable
            journal_lines.append(
                JournalLine(
                    company_id=payment.company_id,
                    account_id=payment.bank_or_cash_account_id,
                    line_no=1,
                    debit=payment.amount,
                    credit=Decimal("0.00"),
                    description=f"Customer receipt #{payment.id}{ref_text} - {partner_name}",
                )
            )
            journal_lines.append(
                JournalLine(
                    company_id=payment.company_id,
                    account_id=payment.receivable_or_payable_account_id,
                    line_no=2,
                    debit=Decimal("0.00"),
                    credit=payment.amount,
                    description=f"Customer receipt #{payment.id}{ref_text} - {partner_name}",
                )
            )
        else:
            # Vendor Payment: Debit Accounts Payable, Credit Bank/Cash
            journal_lines.append(
                JournalLine(
                    company_id=payment.company_id,
                    account_id=payment.receivable_or_payable_account_id,
                    line_no=1,
                    debit=payment.amount,
                    credit=Decimal("0.00"),
                    description=f"Vendor payment #{payment.id}{ref_text} - {partner_name}",
                )
            )
            journal_lines.append(
                JournalLine(
                    company_id=payment.company_id,
                    account_id=payment.bank_or_cash_account_id,
                    line_no=2,
                    debit=Decimal("0.00"),
                    credit=payment.amount,
                    description=f"Vendor payment #{payment.id}{ref_text} - {partner_name}",
                )
            )

        now = datetime.now(timezone.utc)
        journal_entry = JournalEntry(
            company_id=payment.company_id,
            fiscal_year_id=command.fiscal_year_id,
            fiscal_period_id=command.fiscal_period_id,
            entry_no=entry_no,
            entry_date=payment.payment_date,
            description=f"{entry_prefix} #{payment.id}: {payment.memo or ''}".strip(),
            status="posted",
            source_type=payment.payment_type,
            source_id=str(payment.id),
            created_by_user_id=command.posted_by_user_id,
            posted_at=now,
            lines=journal_lines,
        )

        self._db.add(journal_entry)
        flush_or_rollback(self._db)

        payment.journal_entry_id = journal_entry.id
        payment.status = "posted"

        # Update invoice status if fully settled
        for alloc in payment.allocations:
            invoice = self._db.scalar(
                select(Invoice)
                .execution_options(populate_existing=True)
                .options(
                    selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment)
                )
                .where(Invoice.id == alloc.invoice_id)
            )
            if invoice:
                alloc_sum = sum(
                    (
                        a.amount
                        for a in invoice.allocations
                        if a.payment_id == payment.id or (a.payment and a.payment.status == "posted")
                    ),
                    Decimal("0.00"),
                )
                if alloc_sum >= invoice.total_amount:
                    invoice.status = "paid"

        flush_or_rollback(self._db)
        return self._to_dto(payment)

    def void(self, command: VoidPaymentCommand) -> PaymentDTO:
        payment = self._db.scalar(
            select(Payment)
            .options(
                selectinload(Payment.partner),
                selectinload(Payment.bank_or_cash_account),
                selectinload(Payment.receivable_or_payable_account),
                selectinload(Payment.allocations).selectinload(PaymentAllocation.invoice),
            )
            .where(Payment.id == command.payment_id)
        )
        if payment is None:
            raise ValueError(f"Payment {command.payment_id} not found.")

        if payment.status == "void":
            return self._to_dto(payment)

        # Void linked JournalEntry
        if payment.journal_entry_id:
            journal_entry = self._db.scalar(
                select(JournalEntry).where(JournalEntry.id == payment.journal_entry_id)
            )
            if journal_entry and journal_entry.status != "void":
                journal_entry.status = "void"

        payment.status = "void"

        # Check and update invoice statuses
        for alloc in payment.allocations:
            invoice = self._db.scalar(
                select(Invoice)
                .execution_options(populate_existing=True)
                .options(
                    selectinload(Invoice.allocations).selectinload(PaymentAllocation.payment)
                )
                .where(Invoice.id == alloc.invoice_id)
            )
            if invoice and invoice.status == "paid":
                alloc_sum = sum(
                    (
                        a.amount
                        for a in invoice.allocations
                        if a.payment_id != payment.id and a.payment and a.payment.status == "posted"
                    ),
                    Decimal("0.00"),
                )
                if alloc_sum < invoice.total_amount:
                    invoice.status = "posted"

        flush_or_rollback(self._db)
        return self._to_dto(payment)
