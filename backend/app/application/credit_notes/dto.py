"""Framework-neutral data transfer objects for credit/debit note use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CreditNoteLineDTO:
    id: int
    credit_note_id: int
    line_no: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    account_id: int


@dataclass(frozen=True, slots=True)
class CreateCreditNoteLineCommand:
    description: str
    quantity: Decimal
    unit_price: Decimal
    account_id: int


@dataclass(frozen=True, slots=True)
class CreditNoteAllocationDTO:
    id: int
    company_id: int
    credit_note_id: int
    invoice_id: int
    amount: Decimal
    created_at: datetime | None = None
    invoice_no: str | None = None


@dataclass(frozen=True, slots=True)
class CreateCreditNoteAllocationCommand:
    invoice_id: int
    amount: Decimal


@dataclass(frozen=True, slots=True)
class CreditNoteDTO:
    id: int
    company_id: int
    partner_id: int
    note_type: str  # customer_credit_note, vendor_debit_note
    credit_note_no: str
    issue_date: date
    currency: str
    status: str  # draft, posted, void
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
    lines: list[CreditNoteLineDTO] = field(default_factory=list)
    allocations: list[CreditNoteAllocationDTO] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class CreateCreditNoteCommand:
    company_id: int
    partner_id: int
    note_type: str
    credit_note_no: str
    issue_date: date
    currency: str
    lines: list[CreateCreditNoteLineCommand]
    reference: str | None = None
    tax_amount: Decimal = Decimal("0.00")
    reason: str | None = None
    created_by_user_id: int | None = None
    allocations: list[CreateCreditNoteAllocationCommand] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PostCreditNoteCommand:
    credit_note_id: int
    receivable_or_payable_account_id: int
    fiscal_year_id: int
    fiscal_period_id: int
    posted_by_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class VoidCreditNoteCommand:
    credit_note_id: int
    voided_by_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class AllocateCreditNoteCommand:
    credit_note_id: int
    allocations: list[CreateCreditNoteAllocationCommand]


@dataclass(frozen=True, slots=True)
class CreditNoteQuery:
    company_id: int
    note_type: str | None = None
    partner_id: int | None = None
    status: str | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    search: str | None = None
    skip: int = 0
    limit: int = 100


@dataclass(frozen=True, slots=True)
class CreditNotePageDTO:
    items: list[CreditNoteDTO]
    total: int
    skip: int
    limit: int
