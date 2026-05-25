import requests


BASE_URL = "http://127.0.0.1:8010"


def login_and_get_headers():
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "admin@example.com",
            "password": "Password123",
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


def test_company_users_require_authentication():
    response = requests.get(
        f"{BASE_URL}/company-users?company_id=3",
    )

    assert response.status_code in (401, 403)


def test_company_users_work_with_token():
    headers = login_and_get_headers()

    response = requests.get(
        f"{BASE_URL}/company-users?company_id=3",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) > 0

    first_link = data[0]

    assert "id" in first_link
    assert "company_id" in first_link
    assert "user_id" in first_link
    assert "role" in first_link
    assert "is_active" in first_link
    assert first_link["company_id"] == 3