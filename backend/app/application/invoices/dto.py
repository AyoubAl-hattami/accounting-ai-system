"""Framework-neutral data transfer objects for invoice use cases."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class InvoiceLineDTO:
    id: int
    invoice_id: int
    line_no: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    account_id: int


@dataclass(frozen=True, slots=True)
class CreateInvoiceLineCommand:
    description: str
    quantity: Decimal
    unit_price: Decimal
    account_id: int


@dataclass(frozen=True, slots=True)
class InvoiceDTO:
    id: int
    company_id: int
    partner_id: int
    invoice_type: str
    invoice_no: str
    issue_date: date
    due_date: date
    currency: str
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal = Decimal("0.00")
    credited_amount: Decimal = Decimal("0.00")
    residual_amount: Decimal = Decimal("0.00")
    payment_status: str = "unpaid"
    reference: str | None = None
    partner_name: str | None = None
    journal_entry_id: int | None = None
    notes: str | None = None
    created_by_user_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    lines: list[InvoiceLineDTO] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class CreateInvoiceCommand:
    company_id: int
    partner_id: int
    invoice_type: str
    invoice_no: str
    issue_date: date
    due_date: date
    currency: str
    lines: list[CreateInvoiceLineCommand]
    reference: str | None = None
    tax_amount: Decimal = Decimal("0.00")
    notes: str | None = None
    created_by_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class UpdateInvoiceCommand:
    invoice_id: int
    partner_id: int | None = None
    reference: str | None = None
    issue_date: date | None = None
    due_date: date | None = None
    tax_amount: Decimal | None = None
    notes: str | None = None
    lines: list[CreateInvoiceLineCommand] | None = None
    fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class PostInvoiceCommand:
    invoice_id: int
    receivable_or_payable_account_id: int
    fiscal_year_id: int
    fiscal_period_id: int
    posted_by_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class VoidInvoiceCommand:
    invoice_id: int
    voided_by_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class InvoiceQuery:
    company_id: int
    invoice_type: str | None = None
    partner_id: int | None = None
    status: str | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    search: str | None = None
    skip: int = 0
    limit: int = 100


@dataclass(frozen=True, slots=True)
class InvoicePageDTO:
    items: list[InvoiceDTO]
    total: int
    skip: int
    limit: int
