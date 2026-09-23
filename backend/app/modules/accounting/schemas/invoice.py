from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

InvoiceType = Literal["out_invoice", "in_invoice"]
InvoiceStatus = Literal["draft", "posted", "paid", "void", "cancelled"]


class InvoiceLineCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=255)
    quantity: Decimal = Field(default=Decimal("1.0000"), gt=0)
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    account_id: int = Field(..., ge=1)


class InvoiceLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int | None = None
    line_no: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    account_id: int


class InvoiceCreate(BaseModel):
    company_id: int = Field(..., ge=1)
    partner_id: int = Field(..., ge=1)
    invoice_type: InvoiceType
    invoice_no: str = Field(..., min_length=1, max_length=50)
    issue_date: date
    due_date: date
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    reference: str | None = Field(default=None, max_length=100)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    notes: str | None = None
    lines: list[InvoiceLineCreate] = Field(..., min_length=1)

    @field_validator("currency")
    @classmethod
    def _normalise_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip().upper()
        if len(stripped) != 3 or not stripped.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return stripped


class InvoiceUpdate(BaseModel):
    partner_id: int | None = Field(default=None, ge=1)
    reference: str | None = Field(default=None, max_length=100)
    issue_date: date | None = None
    due_date: date | None = None
    tax_amount: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None
    lines: list[InvoiceLineCreate] | None = None


class InvoicePostRequest(BaseModel):
    receivable_or_payable_account_id: int | None = Field(default=None, ge=1)


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    partner_id: int
    partner_name: str | None = None
    invoice_type: InvoiceType
    invoice_no: str
    reference: str | None = None
    issue_date: date
    due_date: date
    currency: str
    status: InvoiceStatus
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal = Decimal("0.00")
    residual_amount: Decimal = Decimal("0.00")
    payment_status: str = "unpaid"
    journal_entry_id: int | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    lines: list[InvoiceLineResponse] = Field(default_factory=list)


class InvoicePageResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    skip: int
    limit: int
