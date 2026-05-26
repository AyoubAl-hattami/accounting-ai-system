import requests


BASE_URL = "http://127.0.0.1:8010"
COMPANY_ID = 3


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


def test_seed_default_accounts_requires_authentication():
    response = requests.post(
        f"{BASE_URL}/accounts/seed-defaults?company_id={COMPANY_ID}",
    )

    assert response.status_code in (401, 403)


def test_seed_default_accounts_with_token():
    headers = login_and_get_headers()

    response = requests.post(
        f"{BASE_URL}/accounts/seed-defaults?company_id={COMPANY_ID}",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == COMPANY_ID
    assert "created_count" in data
    assert "skipped_count" in data
    assert "message" in data
    assert "accounts" in data

    assert data["created_count"] >= 0
    assert data["skipped_count"] >= 0

    accounts_response = requests.get(
        f"{BASE_URL}/accounts?company_id={COMPANY_ID}",
        headers=headers,
    )

    assert accounts_response.status_code == 200

    accounts_data = accounts_response.json()

    assert "items" in accounts_data
    assert "total" in accounts_data
    assert "skip" in accounts_data
    assert "limit" in accounts_data

    accounts = accounts_data["items"]
    account_codes = [account["code"] for account in accounts]

    assert "1000" in account_codes
    assert "1110" in account_codes
    assert "3100" in account_codes
    assert "4100" in account_codes
    assert "5200" in account_codes

    assert len(account_codes) == len(set(account_codes))