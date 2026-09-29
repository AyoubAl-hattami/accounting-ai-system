from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RefundCreate(BaseModel):
    company_id: int
    partner_id: int
    refund_type: str = Field(..., pattern="^(customer_refund|vendor_refund)$")
    currency_code: str = Field(..., min_length=3, max_length=3)
    amount: Decimal = Field(..., gt=Decimal("0.00"))
    refund_date: date
    bank_or_cash_account_id: int
    receivable_or_payable_account_id: int
    credit_note_id: int | None = None
    reference: str | None = Field(None, max_length=100)
    memo: str | None = None


class RefundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    partner_id: int
    refund_type: str
    currency_code: str
    amount: Decimal
    refund_date: date
    bank_or_cash_account_id: int
    receivable_or_payable_account_id: int
    status: str
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


class RefundListRead(BaseModel):
    items: list[RefundRead]
    total: int
    skip: int
    limit: int


class RefundPostRequest(BaseModel):
    fiscal_year_id: int
    fiscal_period_id: int
