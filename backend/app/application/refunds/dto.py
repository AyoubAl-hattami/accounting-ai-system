"""Framework-neutral data transfer objects for refund use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RefundDTO:
    id: int
    company_id: int
    partner_id: int
    refund_type: str  # customer_refund, vendor_refund
    currency_code: str
    amount: Decimal
    refund_date: date
    bank_or_cash_account_id: int
    receivable_or_payable_account_id: int
    status: str  # draft, posted, void
    credit_note_id: int | None = None
    reference: str | None = None
    memo: str | None = None
    journal_entry_id: int | None = None
    created_by_user_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    partner_name: str | None = None
    bank_account_name: str | None = None
    receivable_or_payable_account_name: str | None = None


@dataclass(frozen=True, slots=True)
class CreateRefundCommand:
    company_id: int
    partner_id: int
    refund_type: str  # customer_refund, vendor_refund
    currency_code: str
    amount: Decimal
    refund_date: date
    bank_or_cash_account_id: int
    receivable_or_payable_account_id: int
    credit_note_id: int | None = None
    reference: str | None = None
    memo: str | None = None
    created_by_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class PostRefundCommand:
    refund_id: int
    fiscal_year_id: int
    fiscal_period_id: int
    posted_by_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class VoidRefundCommand:
    refund_id: int
    voided_by_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class RefundQuery:
    company_id: int
    refund_type: str | None = None
    partner_id: int | None = None
    status: str | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    search: str | None = None
    skip: int = 0
    limit: int = 100


@dataclass(frozen=True, slots=True)
class RefundPageDTO:
    items: list[RefundDTO]
    total: int
    skip: int
    limit: int
