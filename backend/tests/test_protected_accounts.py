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


def test_accounts_requires_authentication():
    response = requests.get(
        f"{BASE_URL}/accounts?company_id=3",
    )

    assert response.status_code in (401, 403)


def test_accounts_work_with_token():
    headers = login_and_get_headers()

    response = requests.get(
        f"{BASE_URL}/accounts?company_id=3",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) > 0

    account_codes = {account["code"] for account in data}

    assert "1000" in account_codes
    assert "1110" in account_codes