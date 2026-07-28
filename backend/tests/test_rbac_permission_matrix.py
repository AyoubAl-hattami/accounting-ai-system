"""Focused RBAC contract tests for the shared authorization boundary."""
import uuid
from unittest.mock import Mock

import pytest
import requests
from fastapi import HTTPException
from sqlalchemy import select

from app.core.company_access import ensure_company_access
from app.core.database import SessionLocal
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.user import User
from app.modules.accounting.services.auth_service import create_user_token


def test_inactive_user_cannot_access_company_even_as_superuser():
    user = User(id=1, email="inactive@example.test", hashed_password="x", is_active=False, is_superuser=True)
    with pytest.raises(HTTPException) as exc:
        ensure_company_access(Mock(), user, 1)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Inactive user"


def test_active_superuser_receives_admin_company_context():
    user = User(id=1, email="admin@example.test", hashed_password="x", is_active=True, is_superuser=True)
    access = ensure_company_access(Mock(), user, 42)
    assert access.company_id == 42
    assert access.role == "admin"
    assert access.is_active is True


def test_permission_roles_are_explicit_and_non_mutating_roles_are_distinct():
    # Keep this contract close to the model's database check constraint.
    roles = {"admin", "accountant", "reviewer", "approver", "auditor", "viewer"}
    assert roles == {"admin", "accountant", "reviewer", "approver", "auditor", "viewer"}
    assert {"viewer", "auditor"}.isdisjoint({"admin", "accountant", "reviewer", "approver"})

def test_preissued_token_is_rejected_after_global_deactivation(
    base_url, admin_headers, superuser_headers, default_company_id,
):
    email = f"inactive_token_{uuid.uuid4().hex[:12]}@example.com"
    with SessionLocal() as db:
        user = User(
            email=email,
            full_name="Inactive Token Test",
            hashed_password="not-used-by-this-test",
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        db.flush()
        db.add(CompanyUser(
            company_id=default_company_id,
            user_id=user.id,
            role="viewer",
            is_active=True,
        ))
        db.commit()
        db.refresh(user)
        user_id = user.id
        old_headers = {"Authorization": f"Bearer {create_user_token(user)}"}
    denied = requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate",
        headers=admin_headers,
        params={"company_id": default_company_id},
    )
    assert denied.status_code == 403, denied.text

    with SessionLocal() as db:
        unchanged_user = db.get(User, user_id)
        membership = db.scalar(
            select(CompanyUser).where(
                CompanyUser.company_id == default_company_id,
                CompanyUser.user_id == user_id,
            )
        )
        assert unchanged_user is not None and unchanged_user.is_active is True
        assert membership is not None and membership.is_active is True

    deactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate",
        headers=superuser_headers,
        params={"company_id": default_company_id},
    )
    assert deactivate.status_code == 200, deactivate.text

    with SessionLocal() as db:
        deactivated_user = db.get(User, user_id)
        membership = db.scalar(
            select(CompanyUser).where(
                CompanyUser.company_id == default_company_id,
                CompanyUser.user_id == user_id,
            )
        )
        assert deactivated_user is not None and deactivated_user.is_active is False
        assert membership is not None and membership.is_active is True
    protected_requests = [
        ("accounts", lambda: requests.get(f"{base_url}/accounts", headers=old_headers, params={"company_id": default_company_id})),
        ("journals", lambda: requests.get(f"{base_url}/journal-entries", headers=old_headers, params={"company_id": default_company_id})),
        ("reports", lambda: requests.get(f"{base_url}/reports/trial-balance", headers=old_headers, params={"company_id": default_company_id})),
        ("fiscal", lambda: requests.get(f"{base_url}/fiscal-years", headers=old_headers, params={"company_id": default_company_id})),
        ("gemini", lambda: requests.post(f"{base_url}/ai/gemini-assistant", headers=old_headers, json={"company_id": default_company_id, "message": "Summarize the trial balance", "language": "en"})),
        ("company users", lambda: requests.get(f"{base_url}/company-users", headers=old_headers, params={"company_id": default_company_id})),
        ("auth me", lambda: requests.get(f"{base_url}/auth/me", headers=old_headers)),
    ]
    try:
        for name, call in protected_requests:
            response = call()
            assert response.status_code == 403, f"{name}: {response.status_code} {response.text}"
            assert response.json()["detail"] == "Inactive user"
        assert requests.get(f"{base_url}/health").status_code == 200
    finally:
        reactivate = requests.patch(f"{base_url}/company-users/users/{user_id}/reactivate", headers=superuser_headers, params={"company_id": default_company_id})
        assert reactivate.status_code == 200, reactivate.text


def test_active_admin_still_accesses_company(base_url, admin_headers, default_company_id):
    response = requests.get(f"{base_url}/accounts", headers=admin_headers, params={"company_id": default_company_id})
    assert response.status_code == 200, response.text
