from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CreditNoteLineCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=255)
    quantity: Decimal = Field(..., gt=Decimal("0.0000"))
    unit_price: Decimal = Field(..., ge=Decimal("0.00"))
    account_id: int


class CreditNoteLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    credit_note_id: int
    line_no: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    account_id: int


class CreditNoteAllocationCreate(BaseModel):
    invoice_id: int
    amount: Decimal = Field(..., gt=Decimal("0.00"))


class CreditNoteAllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    credit_note_id: int
    invoice_id: int
    amount: Decimal
    created_at: datetime | None = None
    invoice_no: str | None = None


class CreditNoteCreate(BaseModel):
    company_id: int
    partner_id: int
    note_type: str = Field(..., pattern="^(customer_credit_note|vendor_debit_note)$")
    credit_note_no: str = Field(..., min_length=1, max_length=50)
    issue_date: date
    currency: str = Field(..., min_length=3, max_length=3)
    lines: list[CreditNoteLineCreate] = Field(..., min_length=1)
    reference: str | None = Field(None, max_length=100)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    reason: str | None = None
    allocations: list[CreditNoteAllocationCreate] = Field(default_factory=list)


class CreditNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    partner_id: int
    note_type: str
    credit_note_no: str
    issue_date: date
    currency: str
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    allocated_amount: Decimal = Decimal("0.00")
    unallocated_amount: Decimal = Decimal("0.00")
    reference: str | None = None
    partner_name: str | None = None
    journal_entry_id: int | None = None
    reason: str | None = None
    created_by_user_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    lines: list[CreditNoteLineRead] = Field(default_factory=list)
    allocations: list[CreditNoteAllocationRead] = Field(default_factory=list)


class CreditNoteListRead(BaseModel):
    items: list[CreditNoteRead]
    total: int
    skip: int
    limit: int


class CreditNotePostRequest(BaseModel):
    receivable_or_payable_account_id: int
    fiscal_year_id: int
    fiscal_period_id: int


class CreditNoteAllocateRequest(BaseModel):
    allocations: list[CreditNoteAllocationCreate] = Field(..., min_length=1)
