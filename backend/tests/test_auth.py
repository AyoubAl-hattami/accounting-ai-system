import time

import requests


BASE_URL = "http://127.0.0.1:8010"


def test_register_login_and_me():
    unique_email = f"testuser_{int(time.time())}@example.com"
    password = "Password123"

    register_response = requests.post(
        f"{BASE_URL}/auth/register",
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
        f"{BASE_URL}/auth/login",
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
        f"{BASE_URL}/auth/me",
        headers=headers,
    )

    assert me_response.status_code == 200

    me_data = me_response.json()

    assert me_data["email"] == unique_email
    assert me_data["full_name"] == "Test User"
    assert me_data["is_active"] is True