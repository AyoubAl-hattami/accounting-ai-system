"""An account holding a temporary password reaches nothing but the change.

Onboarding hands a client a password over chat or email.  Until the client
replaces it, the credential is known to at least two people, so the system keeps
the account on the change screen instead of letting it work.  These tests pin
that the refusal is deny-by-default, machine-readable, and exempts nobody.
"""

from uuid import uuid4

import pytest
import requests
from sqlalchemy import select

from app.core.password_change_gate import (
    PASSWORD_CHANGE_REQUIRED_CODE,
    PASSWORD_CHANGE_REQUIRED_MESSAGE,
)
from app.core.security import verify_password
from app.modules.accounting.models.audit_log import AuditLog
from app.modules.accounting.models.user import User
from app.modules.accounting.services.auth_service import create_user_token


TEMPORARY_PASSWORD = "T3mpHandover"
NEW_PASSWORD = "Ch0senByTheClient"
CHANGE_ENDPOINT = "/auth/change-temporary-password"
BUSINESS_ENDPOINT = "/accounts"


def _headers(user) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_user_token(user)}"}


def _change_body(**overrides) -> dict:
    body = {
        "current_password": TEMPORARY_PASSWORD,
        "new_password": NEW_PASSWORD,
        "confirm_password": NEW_PASSWORD,
    }
    body.update(overrides)
    return body


@pytest.fixture
def flagged_admin(accounting_factory):
    """A company admin still holding the password it was handed."""
    company = accounting_factory.create_company(name=f"Handed Over {uuid4().hex[:8]}")
    user = accounting_factory.create_user(
        password=TEMPORARY_PASSWORD,
        full_name="Fresh Client Admin",
        must_change_password=True,
    )
    accounting_factory.add_company_user(company=company, user=user, role="admin")
    accounting_factory.set_subscription(company=company, status="active")
    accounting_factory.db.commit()
    return company, user


# ── the flag is visible to the client ─────────────────────────────────────────


def test_login_tells_the_client_the_password_must_change(base_url, flagged_admin):
    _, user = flagged_admin

    login = requests.post(
        f"{base_url}/auth/login",
        json={"email": user.email, "password": TEMPORARY_PASSWORD},
    )

    assert login.status_code == 200, login.text
    assert login.json()["must_change_password"] is True
    assert login.json()["access_token"]


def test_me_exposes_the_flag_and_stays_reachable(base_url, flagged_admin):
    _, user = flagged_admin

    me = requests.get(f"{base_url}/auth/me", headers=_headers(user))

    assert me.status_code == 200, me.text
    assert me.json()["must_change_password"] is True


def test_a_settled_account_reports_the_flag_as_false(base_url, accounting_factory):
    user = accounting_factory.create_user()
    accounting_factory.db.commit()

    me = requests.get(f"{base_url}/auth/me", headers=_headers(user))

    assert me.status_code == 200
    assert me.json()["must_change_password"] is False


# ── what the flag blocks ──────────────────────────────────────────────────────


def test_a_business_endpoint_is_refused_while_the_flag_is_set(
    base_url, flagged_admin
):
    company, user = flagged_admin

    blocked = requests.get(
        f"{base_url}{BUSINESS_ENDPOINT}?company_id={company.id}",
        headers=_headers(user),
    )

    assert blocked.status_code == 403
    detail = blocked.json()["detail"]
    assert detail["code"] == PASSWORD_CHANGE_REQUIRED_CODE
    assert detail["message"] == PASSWORD_CHANGE_REQUIRED_MESSAGE


def test_company_management_is_refused_while_the_flag_is_set(base_url, flagged_admin):
    _, user = flagged_admin

    blocked = requests.get(f"{base_url}/companies", headers=_headers(user))

    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == PASSWORD_CHANGE_REQUIRED_CODE


def test_optional_authentication_does_not_bypass_the_password_gate(
    base_url, flagged_admin
):
    _, user = flagged_admin

    blocked = requests.post(
        f"{base_url}/company-users/invitations/accept",
        headers=_headers(user),
        json={"token": "not-a-real-invitation-token"},
    )

    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == PASSWORD_CHANGE_REQUIRED_CODE


# The platform owner is the one role that could plausibly be exempted, so it is
# the case that proves nobody is.
def test_even_a_platform_admin_is_refused_while_the_flag_is_set(
    base_url, accounting_factory
):
    superuser = accounting_factory.create_user(
        password=TEMPORARY_PASSWORD,
        is_superuser=True,
        must_change_password=True,
    )
    accounting_factory.db.commit()

    listed = requests.get(f"{base_url}/platform/subscriptions", headers=_headers(superuser))
    defaults = requests.get(
        f"{base_url}/platform/onboarding/defaults", headers=_headers(superuser)
    )

    assert listed.status_code == 403
    assert listed.json()["detail"]["code"] == PASSWORD_CHANGE_REQUIRED_CODE
    assert defaults.status_code == 403
    assert defaults.json()["detail"]["code"] == PASSWORD_CHANGE_REQUIRED_CODE


# ── changing the password ─────────────────────────────────────────────────────


def test_the_change_requires_the_current_password(base_url, flagged_admin):
    _, user = flagged_admin

    refused = requests.post(
        f"{base_url}{CHANGE_ENDPOINT}",
        json=_change_body(current_password="N0tThePassword"),
        headers=_headers(user),
    )

    assert refused.status_code == 400
    assert "current password" in str(refused.json()["detail"]).lower()


def test_a_weak_new_password_is_refused(base_url, flagged_admin):
    _, user = flagged_admin

    refused = requests.post(
        f"{base_url}{CHANGE_ENDPOINT}",
        json=_change_body(new_password="alllowercase", confirm_password="alllowercase"),
        headers=_headers(user),
    )

    assert refused.status_code == 422
    assert "uppercase" in str(refused.json()).lower()


def test_a_mismatched_confirmation_is_refused(base_url, flagged_admin):
    _, user = flagged_admin

    refused = requests.post(
        f"{base_url}{CHANGE_ENDPOINT}",
        json=_change_body(confirm_password=NEW_PASSWORD + "X"),
        headers=_headers(user),
    )

    assert refused.status_code == 422


def test_reusing_the_temporary_password_is_refused(base_url, flagged_admin):
    _, user = flagged_admin

    refused = requests.post(
        f"{base_url}{CHANGE_ENDPOINT}",
        json=_change_body(
            new_password=TEMPORARY_PASSWORD, confirm_password=TEMPORARY_PASSWORD
        ),
        headers=_headers(user),
    )

    assert refused.status_code == 422


def test_the_change_clears_the_flag_and_replaces_the_hash(
    base_url, accounting_factory, flagged_admin
):
    _, user = flagged_admin
    original_hash = user.hashed_password

    changed = requests.post(
        f"{base_url}{CHANGE_ENDPOINT}", json=_change_body(), headers=_headers(user)
    )

    assert changed.status_code == 200, changed.text
    assert changed.json()["must_change_password"] is False

    accounting_factory.db.expire_all()
    stored = accounting_factory.db.scalar(select(User).where(User.id == user.id))
    assert stored.must_change_password is False
    assert stored.hashed_password != original_hash
    assert verify_password(NEW_PASSWORD, stored.hashed_password)
    # The plaintext is nowhere on the row, only its hash.
    assert NEW_PASSWORD not in stored.hashed_password


def test_the_business_api_opens_once_the_password_is_changed(
    base_url, accounting_factory, flagged_admin
):
    company, user = flagged_admin

    changed = requests.post(
        f"{base_url}{CHANGE_ENDPOINT}", json=_change_body(), headers=_headers(user)
    )
    assert changed.status_code == 200, changed.text

    accounting_factory.db.expire_all()
    settled = accounting_factory.db.scalar(select(User).where(User.id == user.id))

    allowed = requests.get(
        f"{base_url}{BUSINESS_ENDPOINT}?company_id={company.id}",
        headers=_headers(settled),
    )

    assert allowed.status_code == 200


def test_the_change_is_audited_without_either_password(
    base_url, accounting_factory, flagged_admin
):
    _, user = flagged_admin

    changed = requests.post(
        f"{base_url}{CHANGE_ENDPOINT}", json=_change_body(), headers=_headers(user)
    )
    assert changed.status_code == 200, changed.text

    log = accounting_factory.db.scalar(
        select(AuditLog)
        .where(AuditLog.action == "change_password")
        .where(AuditLog.entity_type == "user")
        .where(AuditLog.entity_id == user.id)
    )

    assert log is not None
    assert log.actor_email == user.email
    recorded = " ".join(
        [
            str(log.description or ""),
            str(log.new_values),
            str(log.old_values),
        ]
    )
    assert TEMPORARY_PASSWORD not in recorded
    assert NEW_PASSWORD not in recorded


def test_the_change_endpoint_requires_authentication(base_url):
    anonymous = requests.post(f"{base_url}{CHANGE_ENDPOINT}", json=_change_body())

    assert anonymous.status_code in (401, 403)


# An account that already cleared the flag keeps the same door for a routine
# rotation, so there is no second endpoint to keep in step.
def test_a_settled_account_can_still_rotate_its_own_password(
    base_url, accounting_factory
):
    user = accounting_factory.create_user(password=TEMPORARY_PASSWORD)
    accounting_factory.db.commit()

    changed = requests.post(
        f"{base_url}{CHANGE_ENDPOINT}", json=_change_body(), headers=_headers(user)
    )

    assert changed.status_code == 200, changed.text
    assert changed.json()["must_change_password"] is False
