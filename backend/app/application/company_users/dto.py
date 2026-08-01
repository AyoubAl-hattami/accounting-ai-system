"""Framework-neutral data transfer objects for company-user use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CreateCompanyUserCommand:
    company_id: int
    user_id: int
    role: str = "viewer"
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class UpdateCompanyUserCommand:
    """Partial-update command.  Only fields present in ``fields`` are applied."""

    company_user_id: int
    fields: frozenset[str]
    role: str | None = None
    is_active: bool | None = None


@dataclass(frozen=True, slots=True)
class CompanyUserDTO:
    """Read projection of a persisted company-user membership record."""

    id: int
    company_id: int
    user_id: int
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    user_email: str | None = None
    user_full_name: str | None = None
    user_is_active: bool = True


@dataclass(frozen=True, slots=True)
class CompanyUserPageDTO:
    items: tuple[CompanyUserDTO, ...]
    total: int
    skip: int
    limit: int
