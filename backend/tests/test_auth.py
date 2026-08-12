import time

import requests
import pytest
from fastapi import HTTPException

from app.modules.accounting.routes import auth_routes
from app.modules.accounting.schemas.user import UserCreate


def test_register_login_and_me(base_url):
    unique_email = f"testuser_{int(time.time())}@example.com"
    password = "Password123"

    register_response = requests.post(
        f"{base_url}/auth/register",
        json={
            "email": unique_email,
            "password": password,
            "full_name": "Test User",
        },
    )

    assert register_response.status_code == 201

    user_data = register_response.json()

    assert user_data["email"] == unique_email
    assert user_data["full_name"] == "Test User"
    assert user_data["is_active"] is True
    assert "hashed_password" not in user_data

    login_response = requests.post(
        f"{base_url}/auth/login",
        json={
            "email": unique_email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    token_data = login_response.json()

    assert token_data["token_type"] == "bearer"
    assert token_data["access_token"]

    headers = {
        "Authorization": f"Bearer {token_data['access_token']}",
    }

    me_response = requests.get(
        f"{base_url}/auth/me",
        headers=headers,
    )

    assert me_response.status_code == 200

    me_data = me_response.json()

    assert me_data["email"] == unique_email
    assert me_data["full_name"] == "Test User"
    assert me_data["is_active"] is True


def test_registration_is_rejected_when_public_enrollment_is_disabled(monkeypatch):
    monkeypatch.setattr(auth_routes.settings, "PUBLIC_REGISTRATION_ENABLED", False)

    with pytest.raises(HTTPException) as exc_info:
        auth_routes.register_endpoint(
            UserCreate(
                email="blocked-registration@accounting-ai-test.dev",
                password="Password123",
                full_name="Blocked Registration",
            ),
            request=None,
            db=None,
        )

    assert exc_info.value.status_code == 404
    assert "not available" in exc_info.value.detail
