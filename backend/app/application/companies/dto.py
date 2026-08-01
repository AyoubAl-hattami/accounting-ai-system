"""Framework-neutral data transfer objects for company use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CreateCompanyCommand:
    name: str
    base_currency: str
    legal_name: str | None = None
    registration_no: str | None = None
    tax_no: str | None = None
    address: str | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class UpdateCompanyCommand:
    """Partial-update command.  Only fields present in ``fields`` are applied."""

    company_id: int
    fields: frozenset[str]
    name: str | None = None
    legal_name: str | None = None
    registration_no: str | None = None
    tax_no: str | None = None
    base_currency: str | None = None
    address: str | None = None
    is_active: bool | None = None


@dataclass(frozen=True, slots=True)
class CompanyDTO:
    """Read projection of a persisted company record."""

    id: int
    name: str
    base_currency: str
    created_at: datetime
    updated_at: datetime
    legal_name: str | None = None
    registration_no: str | None = None
    tax_no: str | None = None
    address: str | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class CompanyPageDTO:
    items: tuple[CompanyDTO, ...]
    total: int
    skip: int
    limit: int
