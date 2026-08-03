"""Pure subscription status and expiry rules.

Effective status is computed on every read rather than persisted by a cron job,
so a subscription that lapses between two requests is enforced immediately.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timezone

STATUS_TRIAL = "trial"
STATUS_ACTIVE = "active"
STATUS_PAST_DUE = "past_due"
STATUS_SUSPENDED = "suspended"
STATUS_CANCELLED = "cancelled"

VALID_STATUSES = frozenset(
    {
        STATUS_TRIAL,
        STATUS_ACTIVE,
        STATUS_PAST_DUE,
        STATUS_SUSPENDED,
        STATUS_CANCELLED,
    }
)

# Statuses that still grant access once expiry has been taken into account.
GRANTING_STATUSES = frozenset({STATUS_TRIAL, STATUS_ACTIVE})

# Statuses a platform admin must lift explicitly; extending the date alone does
# not resurrect them.
TERMINAL_STATUSES = frozenset({STATUS_SUSPENDED, STATUS_CANCELLED})


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    """Treat naive timestamps as UTC so comparisons never raise."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def effective_status(
    status: str,
    expires_at: datetime | None,
    now: datetime | None = None,
) -> str:
    """Return the status the system should act on, not the stored one."""
    if status in TERMINAL_STATUSES or status == STATUS_PAST_DUE:
        return status

    if expires_at is None:
        return status

    moment = _as_aware(now or utc_now())
    if _as_aware(expires_at) <= moment:
        return STATUS_PAST_DUE

    return status


def grants_access(
    status: str,
    expires_at: datetime | None,
    now: datetime | None = None,
) -> bool:
    return effective_status(status, expires_at, now) in GRANTING_STATUSES


def days_remaining(
    expires_at: datetime | None,
    now: datetime | None = None,
) -> int | None:
    """Whole days left before expiry.  Negative once lapsed, None if unlimited."""
    if expires_at is None:
        return None

    moment = _as_aware(now or utc_now())
    delta = _as_aware(expires_at) - moment
    return delta.days if delta.total_seconds() >= 0 else -((-delta).days + 1)


def add_months(moment: datetime, months: int) -> datetime:
    """Add calendar months, clamping to the last valid day of the target month."""
    total = moment.month - 1 + months
    year = moment.year + total // 12
    month = total % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def extended_expiry(
    expires_at: datetime | None,
    *,
    months: int = 0,
    years: int = 0,
    now: datetime | None = None,
) -> datetime:
    """Extend from the current expiry, or from now when already lapsed."""
    moment = _as_aware(now or utc_now())
    base = _as_aware(expires_at) if expires_at is not None else moment
    if base < moment:
        base = moment
    return add_months(base, months + years * 12)
