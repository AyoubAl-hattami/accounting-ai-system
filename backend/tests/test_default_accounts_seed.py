import uuid
import requests


def _create_company(base_url, headers, name_prefix):
    response = requests.post(
        f"{base_url}/companies",
        headers=headers,
        json={
            "name": f"{name_prefix} {uuid.uuid4().hex}",
            "base_currency": "USD",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_seed_default_accounts_requires_authentication(base_url):
    response = requests.post(
        f"{base_url}/accounts/seed-defaults?company_id=1",
    )

    assert response.status_code in (401, 403)


def test_seed_default_accounts_with_token(
    base_url,
    deterministic_accounting_bootstrap,
):
    headers = deterministic_accounting_bootstrap.auth_headers
    company_id = _create_company(base_url, headers, "Seed defaults")

    response = requests.post(
        f"{base_url}/accounts/seed-defaults?company_id={company_id}",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == company_id
    assert "created_count" in data
    assert "skipped_count" in data
    assert "message" in data
    assert "accounts" in data

    assert data["created_count"] >= 0
    assert data["skipped_count"] >= 0

    accounts_response = requests.get(
        f"{base_url}/accounts?company_id={company_id}",
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
    assert "3200" in account_codes
    assert "4100" in account_codes
    assert "5200" in account_codes

    assert len(account_codes) == len(set(account_codes))

def test_seed_default_accounts_is_idempotent_with_exact_result_contract(
    base_url,
    deterministic_accounting_bootstrap,
):
    headers = deterministic_accounting_bootstrap.auth_headers
    company_id = _create_company(base_url, headers, "Seed idempotency")

    first = requests.post(
        f"{base_url}/accounts/seed-defaults?company_id={company_id}",
        headers=headers,
    )
    second = requests.post(
        f"{base_url}/accounts/seed-defaults?company_id={company_id}",
        headers=headers,
    )

    assert first.status_code == 200
    assert first.json()["company_id"] == company_id
    assert first.json()["created_count"] == 13
    assert first.json()["skipped_count"] == 0
    assert first.json()["message"] == "Default chart of accounts seeded successfully"
    assert len(first.json()["accounts"]) == 13
    assert all(account["is_system"] for account in first.json()["accounts"])
    assert second.status_code == 200
    assert second.json() == {
        "company_id": company_id,
        "created_count": 0,
        "skipped_count": 13,
        "message": "Default chart of accounts seeded successfully",
        "accounts": [],
    }
