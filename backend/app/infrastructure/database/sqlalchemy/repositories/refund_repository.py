from __future__ import annotations

"""SQLAlchemy adapter for refund persistence and GL posting."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.application.refunds.dto import (
    CreateRefundCommand,
    PostRefundCommand,
    RefundDTO,
    RefundPageDTO,
    RefundQuery,
    VoidRefundCommand,
)
from app.application.refunds.ports import RefundRepository
from app.core.database import flush_or_rollback
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.credit_note import CreditNote
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.partner import Partner
from app.modules.accounting.models.refund import Refund


class SqlAlchemyRefundRepository(RefundRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    @classmethod
    def _to_dto(cls, refund: Refund) -> RefundDTO:
        partner_name = refund.partner.name if refund.partner else None
        bank_name = (
            refund.bank_or_cash_account.name
            if refund.bank_or_cash_account
            else None
        )
        ar_ap_name = (
            refund.receivable_or_payable_account.name
            if refund.receivable_or_payable_account
            else None
        )

        return RefundDTO(
            id=refund.id,
            company_id=refund.company_id,
            partner_id=refund.partner_id,
            refund_type=refund.refund_type,
            currency_code=refund.currency_code,
            amount=refund.amount,
            refund_date=refund.refund_date,
            bank_or_cash_account_id=refund.bank_or_cash_account_id,
            receivable_or_payable_account_id=refund.receivable_or_payable_account_id,
            status=refund.status,
            credit_note_id=refund.credit_note_id,
            reference=refund.reference,
            memo=refund.memo,
            journal_entry_id=refund.journal_entry_id,
            created_by_user_id=refund.created_by_user_id,
            created_at=refund.created_at,
            updated_at=refund.updated_at,
            partner_name=partner_name,
            bank_account_name=bank_name,
            receivable_or_payable_account_name=ar_ap_name,
        )

    def create(self, command: CreateRefundCommand) -> RefundDTO:
        if command.amount <= Decimal("0.00"):
            raise ValueError("Refund amount must be greater than zero.")

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
                f"Partner currency '{partner.currency}' does not match refund currency '{command.currency_code}'."
            )

        if command.refund_type == "customer_refund" and not partner.is_customer:
            raise ValueError("The selected partner is not marked as a customer.")
        if command.refund_type == "vendor_refund" and not partner.is_vendor:
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
                f"Bank/Cash account currency '{bank_account.currency}' does not match refund currency '{command.currency_code}'."
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
                f"Receivable/Payable account currency '{ar_ap_account.currency}' does not match refund currency '{command.currency_code}'."
            )

        if command.credit_note_id is not None:
            cn = self._db.scalar(
                select(CreditNote).where(
                    CreditNote.id == command.credit_note_id,
                    CreditNote.company_id == command.company_id,
                )
            )
            if cn is None:
                raise ValueError(f"Credit note {command.credit_note_id} not found.")
            if cn.partner_id != command.partner_id:
                raise ValueError("Credit note does not belong to the selected partner.")
            if cn.currency != command.currency_code:
                raise ValueError("Credit note currency does not match refund currency.")
            if cn.status != "posted":
                raise ValueError(f"Cannot refund credit note in status '{cn.status}'. Must be 'posted'.")

        refund = Refund(
            company_id=command.company_id,
            partner_id=command.partner_id,
            refund_type=command.refund_type,
            currency_code=command.currency_code,
            amount=command.amount,
            refund_date=command.refund_date,
            bank_or_cash_account_id=command.bank_or_cash_account_id,
            receivable_or_payable_account_id=command.receivable_or_payable_account_id,
            credit_note_id=command.credit_note_id,
            reference=command.reference,
            memo=command.memo,
            status="draft",
            created_by_user_id=command.created_by_user_id,
        )

        self._db.add(refund)
        flush_or_rollback(self._db)
        self._db.refresh(
            refund,
            ["partner", "bank_or_cash_account", "receivable_or_payable_account"],
        )
        return self._to_dto(refund)

    def get_by_id(self, refund_id: int) -> RefundDTO | None:
        refund = self._db.scalar(
            select(Refund)
            .options(
                selectinload(Refund.partner),
                selectinload(Refund.bank_or_cash_account),
                selectinload(Refund.receivable_or_payable_account),
            )
            .where(Refund.id == refund_id)
        )
        return self._to_dto(refund) if refund else None

    def list(self, query: RefundQuery) -> RefundPageDTO:
        statement = select(Refund).where(Refund.company_id == query.company_id)

        if query.refund_type is not None:
            statement = statement.where(Refund.refund_type == query.refund_type)
        if query.partner_id is not None:
            statement = statement.where(Refund.partner_id == query.partner_id)
        if query.status is not None:
            statement = statement.where(Refund.status == query.status)
        if query.currency is not None:
            statement = statement.where(Refund.currency_code == query.currency)
        if query.start_date is not None:
            statement = statement.where(Refund.refund_date >= query.start_date)
        if query.end_date is not None:
            statement = statement.where(Refund.refund_date <= query.end_date)
        if query.search:
            pattern = f"%{query.search.strip()}%"
            statement = statement.where(
                or_(
                    Refund.reference.ilike(pattern),
                    Refund.memo.ilike(pattern),
                )
            )

        total = self._db.scalar(
            select(func.count()).select_from(statement.subquery())
        ) or 0

        statement = (
            statement.options(
                selectinload(Refund.partner),
                selectinload(Refund.bank_or_cash_account),
                selectinload(Refund.receivable_or_payable_account),
            )
            .order_by(Refund.refund_date.desc(), Refund.id.desc())
            .offset(query.skip)
            .limit(query.limit)
        )
        refunds = self._db.scalars(statement).all()

        return RefundPageDTO(
            items=[self._to_dto(r) for r in refunds],
            total=total,
            skip=query.skip,
            limit=query.limit,
        )

    def post(self, command: PostRefundCommand) -> RefundDTO:
        refund = self._db.scalar(
            select(Refund)
            .options(
                selectinload(Refund.partner),
                selectinload(Refund.bank_or_cash_account),
                selectinload(Refund.receivable_or_payable_account),
            )
            .where(Refund.id == command.refund_id)
        )
        if refund is None:
            raise ValueError(f"Refund {command.refund_id} not found.")

        if refund.status != "draft":
            raise ValueError(f"Cannot post refund in status '{refund.status}'. Must be 'draft'.")

        # Validate accounts & currency
        bank_account = refund.bank_or_cash_account
        if bank_account.currency != refund.currency_code:
            raise ValueError(
                f"Bank/Cash account currency '{bank_account.currency}' does not match refund currency '{refund.currency_code}'."
            )

        ar_ap_account = refund.receivable_or_payable_account
        if ar_ap_account.currency != refund.currency_code:
            raise ValueError(
                f"Receivable/Payable account currency '{ar_ap_account.currency}' does not match refund currency '{refund.currency_code}'."
            )

        if refund.partner.currency and refund.partner.currency != refund.currency_code:
            raise ValueError(
                f"Partner currency '{refund.partner.currency}' does not match refund currency '{refund.currency_code}'."
            )

        # Generate Journal Entry
        entry_prefix = "CRF" if refund.refund_type == "customer_refund" else "VRF"
        entry_no = f"{entry_prefix}-{refund.id}"

        journal_lines: list[JournalLine] = []
        partner_name = refund.partner.name if refund.partner else ""
        ref_text = f" ({refund.reference})" if refund.reference else ""

        if refund.refund_type == "customer_refund":
            # Customer Refund (we send money back to customer):
            # Debit Accounts Receivable, Credit Bank/Cash
            journal_lines.append(
                JournalLine(
                    company_id=refund.company_id,
                    account_id=refund.receivable_or_payable_account_id,
                    line_no=1,
                    debit=refund.amount,
                    credit=Decimal("0.00"),
                    description=f"Customer refund #{refund.id}{ref_text} - {partner_name}",
                )
            )
            journal_lines.append(
                JournalLine(
                    company_id=refund.company_id,
                    account_id=refund.bank_or_cash_account_id,
                    line_no=2,
                    debit=Decimal("0.00"),
                    credit=refund.amount,
                    description=f"Customer refund #{refund.id}{ref_text} - {partner_name}",
                )
            )
        else:
            # Vendor Refund (vendor sends money back to us):
            # Debit Bank/Cash, Credit Accounts Payable
            journal_lines.append(
                JournalLine(
                    company_id=refund.company_id,
                    account_id=refund.bank_or_cash_account_id,
                    line_no=1,
                    debit=refund.amount,
                    credit=Decimal("0.00"),
                    description=f"Vendor refund #{refund.id}{ref_text} - {partner_name}",
                )
            )
            journal_lines.append(
                JournalLine(
                    company_id=refund.company_id,
                    account_id=refund.receivable_or_payable_account_id,
                    line_no=2,
                    debit=Decimal("0.00"),
                    credit=refund.amount,
                    description=f"Vendor refund #{refund.id}{ref_text} - {partner_name}",
                )
            )

        now = datetime.now(timezone.utc)
        journal_entry = JournalEntry(
            company_id=refund.company_id,
            fiscal_year_id=command.fiscal_year_id,
            fiscal_period_id=command.fiscal_period_id,
            entry_no=entry_no,
            entry_date=refund.refund_date,
            description=f"{entry_prefix} #{refund.id}: {refund.memo or ''}".strip(),
            status="posted",
            source_type=refund.refund_type,
            source_id=str(refund.id),
            created_by_user_id=command.posted_by_user_id,
            posted_at=now,
            lines=journal_lines,
        )

        self._db.add(journal_entry)
        flush_or_rollback(self._db)

        refund.journal_entry_id = journal_entry.id
        refund.status = "posted"

        flush_or_rollback(self._db)
        return self._to_dto(refund)

    def void(self, command: VoidRefundCommand) -> RefundDTO:
        refund = self._db.scalar(
            select(Refund)
            .options(
                selectinload(Refund.partner),
                selectinload(Refund.bank_or_cash_account),
                selectinload(Refund.receivable_or_payable_account),
            )
            .where(Refund.id == command.refund_id)
        )
        if refund is None:
            raise ValueError(f"Refund {command.refund_id} not found.")

        if refund.status == "void":
            return self._to_dto(refund)

        if refund.journal_entry_id:
            journal_entry = self._db.scalar(
                select(JournalEntry).where(JournalEntry.id == refund.journal_entry_id)
            )
            if journal_entry and journal_entry.status != "void":
                journal_entry.status = "void"

        refund.status = "void"
        flush_or_rollback(self._db)
        return self._to_dto(refund)
