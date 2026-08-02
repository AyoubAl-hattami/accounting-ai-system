"""Invitation create / validate / accept contract tests."""
import uuid

import pytest
import requests


def test_create_invitation_success(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    unique_id = uuid.uuid4().hex[:6]
    data = {
        "company_id": bs.company_id,
        "email": f"new_invitee_{unique_id}@accounting-ai-test.dev",
        "role": "viewer",
    }
    response = requests.post(
        f"{base_url}/company-users/invitations",
        json=data,
        headers=bs.auth_headers,
    )
    assert response.status_code == 200, response.json()
    content = response.json()
    assert content["status"] == "invited"
    assert "token" in content
    assert "invite_url" in content


def test_create_invitation_already_member(
    base_url, deterministic_accounting_bootstrap
):
    """Inviting an active company member raises a 409 conflict.

    The domain service raises UserAlreadyMember which the route maps to
    HTTP 409 with the exact detail string.  The old soft-error 200 body
    was retired when invitation errors were promoted to domain exceptions.
    """
    bs = deterministic_accounting_bootstrap
    # The factory admin user is already a member of bs.company.
    data = {
        "company_id": bs.company_id,
        "email": bs.user.email,
        "role": "accountant",
    }
    response = requests.post(
        f"{base_url}/company-users/invitations",
        json=data,
        headers=bs.auth_headers,
    )
    assert response.status_code == 409, response.json()
    assert response.json()["detail"] == "User is already a member of this company"


def test_validate_and_accept_invitation_new_user(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    unique_id = uuid.uuid4().hex[:6]
    email = f"accept_test_{unique_id}@accounting-ai-test.dev"
    data = {
        "company_id": bs.company_id,
        "email": email,
        "role": "viewer",
    }
    res_create = requests.post(
        f"{base_url}/company-users/invitations",
        json=data,
        headers=bs.auth_headers,
    )
    assert res_create.status_code == 200, res_create.json()
    token = res_create.json().get("token")

    # Validate
    res_val = requests.get(
        f"{base_url}/company-users/invitations/validate?token={token}"
    )
    assert res_val.status_code == 200
    assert res_val.json()["email"] == email
    assert res_val.json()["user_exists"] is False

    # Accept
    res_accept = requests.post(
        f"{base_url}/company-users/invitations/accept",
        json={
            "token": token,
            "full_name": "New Invitee",
            "password": "SecurePassword123!",
        },
    )
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "success"

    # Validate again — accepted invitations are in a terminal state
    res_val2 = requests.get(
        f"{base_url}/company-users/invitations/validate?token={token}"
    )
    assert res_val2.status_code == 409
