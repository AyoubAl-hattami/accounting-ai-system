"""Unit tests for the pure subscription status and expiry rules."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.application.subscriptions.policy import (
    add_months,
    days_remaining,
    effective_status,
    extended_expiry,
    grants_access,
)
from app.core import subscription_access


NOW = datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc)


def test_active_subscription_without_expiry_stays_active():
    assert effective_status("active", None, NOW) == "active"
    assert grants_access("active", None, NOW) is True


def test_active_subscription_with_future_expiry_stays_active():
    assert effective_status("active", NOW + timedelta(days=1), NOW) == "active"
    assert grants_access("active", NOW + timedelta(days=1), NOW) is True


def test_effective_status_becomes_past_due_when_expiry_is_in_the_past():
    assert effective_status("active", NOW - timedelta(seconds=1), NOW) == "past_due"
    assert effective_status("trial", NOW - timedelta(days=30), NOW) == "past_due"
    assert grants_access("active", NOW - timedelta(seconds=1), NOW) is False


@pytest.mark.parametrize("status", ["suspended", "cancelled", "past_due"])
def test_terminal_statuses_never_grant_access_regardless_of_expiry(status):
    assert effective_status(status, NOW + timedelta(days=365), NOW) == status
    assert grants_access(status, NOW + timedelta(days=365), NOW) is False


def test_naive_expiry_is_treated_as_utc_rather_than_raising():
    assert effective_status("active", datetime(2026, 1, 1), NOW) == "past_due"


def test_days_remaining_is_none_without_expiry_and_negative_once_lapsed():
    assert days_remaining(None, NOW) is None
    assert days_remaining(NOW + timedelta(days=10, hours=2), NOW) == 10
    assert days_remaining(NOW - timedelta(days=1, hours=2), NOW) == -2


def test_add_months_clamps_to_the_last_valid_day():
    assert add_months(datetime(2026, 1, 31), 1) == datetime(2026, 2, 28)
    assert add_months(datetime(2026, 12, 15), 1) == datetime(2027, 1, 15)


def test_extension_of_a_live_subscription_starts_from_its_current_expiry():
    current = NOW + timedelta(days=10)
    assert extended_expiry(current, months=1, now=NOW) == add_months(current, 1)


def test_extension_of_a_lapsed_subscription_starts_from_now():
    assert extended_expiry(NOW - timedelta(days=90), years=1, now=NOW) == add_months(
        NOW, 12
    )


def test_extension_without_an_existing_expiry_starts_from_now():
    assert extended_expiry(None, months=1, now=NOW) == add_months(NOW, 1)


def test_missing_subscription_fails_closed_in_production(monkeypatch):
    class MissingSubscriptionRepository:
        def __init__(self, _db):
            pass

        def get(self, _company_id):
            return None

    monkeypatch.setattr(
        subscription_access, "SqlAlchemySubscriptionRepository", MissingSubscriptionRepository
    )
    monkeypatch.setattr(subscription_access.settings, "APP_ENV", "production")
    monkeypatch.setattr(
        subscription_access.settings, "PRODUCTION_SUBSCRIPTION_FAIL_CLOSED", True
    )

    with pytest.raises(HTTPException) as exc_info:
        subscription_access.ensure_active_subscription(object(), 42)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["status"] == "unmanaged"


def test_missing_subscription_preserves_legacy_development_behavior(monkeypatch):
    class MissingSubscriptionRepository:
        def __init__(self, _db):
            pass

        def get(self, _company_id):
            return None

    monkeypatch.setattr(
        subscription_access, "SqlAlchemySubscriptionRepository", MissingSubscriptionRepository
    )
    monkeypatch.setattr(subscription_access.settings, "APP_ENV", "development")
    subscription_access.ensure_active_subscription(object(), 42)
