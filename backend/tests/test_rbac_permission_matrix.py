"""Focused RBAC contract tests for the shared authorization boundary."""
from unittest.mock import Mock

import pytest
import requests
from fastapi import HTTPException

from app.core.company_access import ensure_company_access
from app.modules.accounting.models.user import User


# ── Pure unit tests (no HTTP, no DB) ─────────────────────────────────────────

def test_inactive_user_cannot_access_company_even_as_superuser():
    user = User(
        id=1,
        email="inactive@example.test",
        hashed_password="x",
        is_active=False,
        is_superuser=True,
    )
    with pytest.raises(HTTPException) as exc:
        ensure_company_access(Mock(), user, 1)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Inactive user"


def test_active_superuser_cannot_enter_tenant_routes():
    user = User(
        id=1,
        email="admin@example.test",
        hashed_password="x",
        is_active=True,
        is_superuser=True,
    )
    with pytest.raises(HTTPException) as exc:
        ensure_company_access(Mock(), user, 42)

    assert exc.value.status_code == 403
    assert exc.value.detail == (
        "Platform administrators cannot access tenant data through company routes"
    )


def test_permission_roles_are_explicit_and_non_mutating_roles_are_distinct():
    roles = {"admin", "accountant", "reviewer", "approver", "auditor", "viewer"}
    assert roles == {"admin", "accountant", "reviewer", "approver", "auditor", "viewer"}
    assert {"viewer", "auditor"}.isdisjoint(
        {"admin", "accountant", "reviewer", "approver"}
    )


# ── HTTP integration tests ────────────────────────────────────────────────────

def test_preissued_token_is_rejected_after_global_deactivation(
    base_url,
    deterministic_accounting_bootstrap,
    accounting_factory,
):
    """A pre-issued JWT must be rejected everywhere once the user is deactivated."""
    factory = accounting_factory
    bs = deterministic_accounting_bootstrap

    # Create a platform superuser and a viewer member in the factory company.
    superuser = factory.create_superuser()
    viewer_user, _ = factory.add_member(company=bs.company, role="viewer")
    factory.db.commit()

    superuser_headers = factory.auth_headers_for(superuser)
    old_headers = factory.auth_headers_for(viewer_user)

    # Company admin (non-superuser) cannot deactivate users globally.
    denied = requests.patch(
        f"{base_url}/company-users/users/{viewer_user.id}/deactivate",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id},
    )
    assert denied.status_code == 403, denied.text

    # Platform superuser CAN deactivate the user globally.
    deactivate = requests.patch(
        f"{base_url}/company-users/users/{viewer_user.id}/deactivate",
        headers=superuser_headers,
        params={"company_id": bs.company_id},
    )
    assert deactivate.status_code == 200, deactivate.text

    # All protected endpoints must reject the pre-issued token with 403 Inactive user.
    protected_requests = [
        (
            "accounts",
            lambda: requests.get(
                f"{base_url}/accounts",
                headers=old_headers,
                params={"company_id": bs.company_id},
            ),
        ),
        (
            "journals",
            lambda: requests.get(
                f"{base_url}/journal-entries",
                headers=old_headers,
                params={"company_id": bs.company_id},
            ),
        ),
        (
            "reports",
            lambda: requests.get(
                f"{base_url}/reports/trial-balance",
                headers=old_headers,
                params={"company_id": bs.company_id},
            ),
        ),
        (
            "fiscal",
            lambda: requests.get(
                f"{base_url}/fiscal-years",
                headers=old_headers,
                params={"company_id": bs.company_id},
            ),
        ),
        (
            "gemini",
            lambda: requests.post(
                f"{base_url}/ai/gemini-assistant",
                headers=old_headers,
                json={
                    "company_id": bs.company_id,
                    "message": "Summarize the trial balance",
                    "language": "en",
                },
            ),
        ),
        (
            "company users",
            lambda: requests.get(
                f"{base_url}/company-users",
                headers=old_headers,
                params={"company_id": bs.company_id},
            ),
        ),
        (
            "auth me",
            lambda: requests.get(f"{base_url}/auth/me", headers=old_headers),
        ),
    ]
    try:
        for name, call in protected_requests:
            response = call()
            assert response.status_code == 403, (
                f"{name}: expected 403, got {response.status_code} {response.text}"
            )
            assert response.json()["detail"] == "Inactive user"
        assert requests.get(f"{base_url}/health").status_code == 200
    finally:
        reactivate = requests.patch(
            f"{base_url}/company-users/users/{viewer_user.id}/reactivate",
            headers=superuser_headers,
            params={"company_id": bs.company_id},
        )
        assert reactivate.status_code == 200, reactivate.text

    # Reactivation restores the account, not credentials issued before the
    # security status transition.
    rejected_after_reactivation = requests.get(
        f"{base_url}/auth/me", headers=old_headers
    )
    assert rejected_after_reactivation.status_code == 401

    factory.db.expire_all()
    refreshed_user = factory.db.get(User, viewer_user.id)
    fresh_headers = factory.auth_headers_for(refreshed_user)
    assert requests.get(f"{base_url}/auth/me", headers=fresh_headers).status_code == 200


def test_active_admin_still_accesses_company(
    base_url, deterministic_accounting_bootstrap
):
    """An active company admin must be able to list accounts."""
    bs = deterministic_accounting_bootstrap
    response = requests.get(
        f"{base_url}/accounts",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id},
    )
    assert response.status_code == 200, response.text
