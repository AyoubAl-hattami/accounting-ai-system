import requests
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

import uuid

def test_create_invitation_success(admin_headers, default_company_id):
    unique_id = uuid.uuid4().hex[:6]
    data = {
        "company_id": default_company_id,
        "email": f"new_invitee_{unique_id}@example.com",
        "role": "viewer"
    }
    response = client.post(
        "/company-users/invitations",
        json=data,
        headers=admin_headers
    )
    if response.status_code != 200:
        print(response.json())
    assert response.status_code == 200
    content = response.json()
    assert content["status"] == "invited"
    assert "token" in content
    assert "invite_url" in content


def test_create_invitation_already_member(base_url, admin_headers, default_company_id):
    # Try to invite the admin themselves, who is already a member
    data = {
        "company_id": default_company_id,
        "email": "admin@example.com",
        "role": "accountant"
    }
    response = requests.post(
        f"{base_url}/company-users/invitations",
        json=data,
        headers=admin_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert content["status"] == "error"
    assert content["message"] == "User is already a member of this company"


def test_validate_and_accept_invitation_new_user(base_url, admin_headers, default_company_id):
    unique_id = uuid.uuid4().hex[:6]
    email = f"accept_test_{unique_id}@example.com"
    data = {
        "company_id": default_company_id,
        "email": email,
        "role": "viewer"
    }
    res_create = requests.post(
        f"{base_url}/company-users/invitations",
        json=data,
        headers=admin_headers
    )
    assert res_create.status_code == 200
    token = res_create.json().get("token")

    # Validate
    res_val = requests.get(f"{base_url}/company-users/invitations/validate?token={token}")
    assert res_val.status_code == 200
    assert res_val.json()["email"] == email
    assert res_val.json()["user_exists"] is False

    # Accept
    res_accept = requests.post(
        f"{base_url}/company-users/invitations/accept",
        json={
            "token": token,
            "full_name": "New Invitee",
            "password": "SecurePassword123!"
        }
    )
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "success"

    # Validate again - accepted invitations have a deterministic conflict state
    res_val2 = requests.get(f"{base_url}/company-users/invitations/validate?token={token}")
    assert res_val2.status_code == 409
