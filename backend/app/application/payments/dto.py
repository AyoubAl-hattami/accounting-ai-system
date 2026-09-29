"""Framework-neutral data transfer objects for payment use cases."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PaymentAllocationDTO:
    id: int
    company_id: int
    payment_id: int
    invoice_id: int
    amount: Decimal
    created_at: datetime | None = None
    invoice_no: str | None = None


@dataclass(frozen=True, slots=True)
class CreatePaymentAllocationCommand:
    invoice_id: int
    amount: Decimal


@dataclass(frozen=True, slots=True)
class PaymentDTO:
    id: int
    company_id: int
    partner_id: int
    payment_type: str  # customer_receipt, vendor_payment
    currency_code: str
    amount: Decimal
    payment_date: date
    bank_or_cash_account_id: int
    receivable_or_payable_account_id: int
    status: str  # draft, posted, void
    reference: str | None = None
    memo: str | None = None
    journal_entry_id: int | None = None
    created_by_user_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    partner_name: str | None = None
    bank_account_name: str | None = None
    receivable_or_payable_account_name: str | None = None
    allocations: list[PaymentAllocationDTO] = field(default_factory=list)
    allocated_amount: Decimal = Decimal("0.00")
    unallocated_amount: Decimal = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class CreatePaymentCommand:
    company_id: int
    partner_id: int
    payment_type: str
    currency_code: str
    amount: Decimal
    payment_date: date
    bank_or_cash_account_id: int
    receivable_or_payable_account_id: int
    allocations: list[CreatePaymentAllocationCommand] = field(default_factory=list)
    reference: str | None = None
    memo: str | None = None
    created_by_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class PostPaymentCommand:
    payment_id: int
    fiscal_year_id: int
    fiscal_period_id: int
    posted_by_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class VoidPaymentCommand:
    payment_id: int
    voided_by_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class PaymentQuery:
    company_id: int
    payment_type: str | None = None
    partner_id: int | None = None
    status: str | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    search: str | None = None
    skip: int = 0
    limit: int = 100


@dataclass(frozen=True, slots=True)
class PaymentPageDTO:
    items: list[PaymentDTO]
    total: int
    skip: int
    limit: int
