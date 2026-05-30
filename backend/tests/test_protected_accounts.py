import requests


def test_accounts_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/accounts?company_id={default_company_id}",
    )

    assert response.status_code in (401, 403)


def test_accounts_work_with_token(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/accounts?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data

    assert isinstance(data["items"], list)
    assert data["total"] > 0

    account_codes = {account["code"] for account in data["items"]}

    assert "1000" in account_codes
    assert "1110" in account_codes


def test_accounts_pagination_metadata(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/accounts?company_id={default_company_id}&skip=0&limit=5",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) <= 5
    assert data["total"] >= len(data["items"])
    assert data["skip"] == 0
    assert data["limit"] == 5