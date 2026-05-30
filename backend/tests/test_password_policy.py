import uuid

import requests


def _unique_email() -> str:
    return f"pwtest_{uuid.uuid4().hex[:12]}@example.com"


def test_password_rejected_without_uppercase(base_url):
    response = requests.post(
        f"{base_url}/auth/register",
        json={
            "email": _unique_email(),
            "password": "password123",
        },
    )

    assert response.status_code == 422

    body = response.json()
    detail_text = str(body)

    assert "uppercase" in detail_text.lower()


def test_password_rejected_without_lowercase(base_url):
    response = requests.post(
        f"{base_url}/auth/register",
        json={
            "email": _unique_email(),
            "password": "PASSWORD123",
        },
    )

    assert response.status_code == 422

    body = response.json()
    detail_text = str(body)

    assert "lowercase" in detail_text.lower()


def test_password_rejected_without_digit(base_url):
    response = requests.post(
        f"{base_url}/auth/register",
        json={
            "email": _unique_email(),
            "password": "Password",
        },
    )

    assert response.status_code == 422

    body = response.json()
    detail_text = str(body)

    assert "digit" in detail_text.lower()


def test_valid_password_registers_successfully(base_url):
    response = requests.post(
        f"{base_url}/auth/register",
        json={
            "email": _unique_email(),
            "password": "Password123",
            "full_name": "Policy Test User",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["is_active"] is True
    assert data["full_name"] == "Policy Test User"
