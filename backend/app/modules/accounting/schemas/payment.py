from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class PaymentAllocationCreate(BaseModel):
    invoice_id: int
    amount: Decimal = Field(..., gt=0)


class PaymentAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    payment_id: int
    invoice_id: int
    amount: Decimal
    created_at: datetime | None = None
    invoice_no: str | None = None


class PaymentCreate(BaseModel):
    company_id: int
    partner_id: int
    payment_type: Literal["customer_receipt", "vendor_payment"]
    currency_code: str = Field(..., min_length=3, max_length=3)
    amount: Decimal = Field(..., gt=0)
    payment_date: date
    bank_or_cash_account_id: int
    receivable_or_payable_account_id: int
    allocations: list[PaymentAllocationCreate] = Field(default_factory=list)
    reference: str | None = Field(None, max_length=100)
    memo: str | None = None


class PaymentPostRequest(BaseModel):
    fiscal_year_id: int | None = None
    fiscal_period_id: int | None = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    partner_id: int
    payment_type: str
    currency_code: str
    amount: Decimal
    payment_date: date
    bank_or_cash_account_id: int
    receivable_or_payable_account_id: int
    status: str
    reference: str | None = None
    memo: str | None = None
    journal_entry_id: int | None = None
    created_by_user_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    partner_name: str | None = None
    bank_account_name: str | None = None
    receivable_or_payable_account_name: str | None = None
    allocations: list[PaymentAllocationResponse] = Field(default_factory=list)
    allocated_amount: Decimal = Decimal("0.00")
    unallocated_amount: Decimal = Decimal("0.00")


class PaymentPageResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    skip: int
    limit: int
