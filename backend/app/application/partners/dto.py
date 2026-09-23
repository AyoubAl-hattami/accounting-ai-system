"""Framework-neutral data transfer objects for partner use cases."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CreatePartnerCommand:
    company_id: int
    name: str
    code: str
    is_customer: bool
    is_vendor: bool
    currency: str = "USD"
    email: str | None = None
    phone: str | None = None
    tax_id: str | None = None
    address: str | None = None
    receivable_account_id: int | None = None
    payable_account_id: int | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class UpdatePartnerCommand:
    partner_id: int
    name: str | None = None
    code: str | None = None
    is_customer: bool | None = None
    is_vendor: bool | None = None
    email: str | None = None
    phone: str | None = None
    tax_id: str | None = None
    address: str | None = None
    receivable_account_id: int | None = None
    payable_account_id: int | None = None
    is_active: bool | None = None
    fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class PartnerQuery:
    company_id: int
    is_customer: bool | None = None
    is_vendor: bool | None = None
    search: str | None = None
    is_active: bool | None = None
    skip: int = 0
    limit: int = 100


@dataclass(frozen=True, slots=True)
class PartnerDTO:
    id: int
    company_id: int
    name: str
    code: str
    is_customer: bool
    is_vendor: bool
    currency: str
    email: str | None
    phone: str | None
    tax_id: str | None
    address: str | None
    receivable_account_id: int | None
    payable_account_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PartnerPageDTO:
    items: list[PartnerDTO]
    total: int
    skip: int
    limit: int
