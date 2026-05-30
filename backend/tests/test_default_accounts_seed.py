import requests


COMPANY_ID = 3


def test_seed_default_accounts_requires_authentication(base_url):
    response = requests.post(
        f"{base_url}/accounts/seed-defaults?company_id={COMPANY_ID}",
    )

    assert response.status_code in (401, 403)


def test_seed_default_accounts_with_token(base_url, admin_headers):
    response = requests.post(
        f"{base_url}/accounts/seed-defaults?company_id={COMPANY_ID}",
        headers=admin_headers,
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
        f"{base_url}/accounts?company_id={COMPANY_ID}",
        headers=admin_headers,
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
    assert "3200" in account_codes
    assert "4100" in account_codes
    assert "5200" in account_codes

    assert len(account_codes) == len(set(account_codes))