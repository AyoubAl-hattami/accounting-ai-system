"""Framework-neutral data transfer objects for client onboarding."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class OnboardClientCommand:
    """Everything needed to stand up one client tenant in a single call.

    ``temporary_password`` is the resolved password — the caller either supplied
    one (already validated against the password policy) or asked for one to be
    generated.  It is never persisted in clear text; the repository hashes it.
    """

    company_name: str
    base_currency: str
    admin_email: str
    temporary_password: str
    admin_full_name: str | None = None
    plan_code: str | None = None
    subscription_status: str = "active"
    subscription_expires_at: datetime | None = None
    trial_ends_at: datetime | None = None
    seed_default_accounts: bool = True
    chart_template: str = "default"
    create_fiscal_year: bool = True
    open_monthly_periods: bool = True
    reuse_existing_user: bool = False
    onboarding_note: str | None = None


@dataclass(frozen=True, slots=True)
class OnboardedClientDTO:
    """Result projection for one completed onboarding.

    Deliberately carries no password: the plaintext exists only in the request
    that created it and in the HTTP response the route assembles.
    """

    company_id: int
    company_name: str
    base_currency: str
    admin_user_id: int
    admin_email: str
    admin_was_existing: bool
    subscription_status: str
    effective_status: str
    plan_code: str | None
    expires_at: datetime | None
    trial_ends_at: datetime | None
    days_remaining: int | None
    seeded_accounts_count: int
    fiscal_year_created: bool
    fiscal_periods_created: int
