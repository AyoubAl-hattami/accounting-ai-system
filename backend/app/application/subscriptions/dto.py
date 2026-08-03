"""Framework-neutral data transfer objects for subscription use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SubscriptionDTO:
    """Read projection of a company subscription record."""

    company_id: int
    status: str
    id: int | None = None
    plan_code: str | None = None
    expires_at: datetime | None = None
    trial_ends_at: datetime | None = None
    suspended_at: datetime | None = None
    cancelled_at: datetime | None = None
    suspension_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CompanySubscriptionDTO:
    """A company joined with its subscription, as the platform admin sees it."""

    company_id: int
    company_name: str
    base_currency: str
    company_is_active: bool
    subscription: SubscriptionDTO
    effective_status: str
    days_remaining: int | None
    member_count: int


@dataclass(frozen=True, slots=True)
class CompanySubscriptionPageDTO:
    items: tuple[CompanySubscriptionDTO, ...]
    total: int
    skip: int
    limit: int


@dataclass(frozen=True, slots=True)
class UpdateSubscriptionCommand:
    """Partial-update command.  Only fields present in ``fields`` are applied."""

    company_id: int
    fields: frozenset[str]
    status: str | None = None
    plan_code: str | None = None
    expires_at: datetime | None = None
    trial_ends_at: datetime | None = None
    suspended_at: datetime | None = None
    cancelled_at: datetime | None = None
    suspension_reason: str | None = None
