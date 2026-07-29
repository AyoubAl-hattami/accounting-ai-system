import uuid

import requests

from app.core.database import SessionLocal
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company


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


def test_authorized_user_can_get_account_by_id(
    base_url,
    admin_headers,
    default_company_id,
):
    list_response = requests.get(
        f"{base_url}/accounts?company_id={default_company_id}&limit=1",
        headers=admin_headers,
    )
    assert list_response.status_code == 200
    account = list_response.json()["items"][0]

    response = requests.get(
        f"{base_url}/accounts/{account['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json() == account


def test_get_account_by_id_returns_existing_not_found_error(
    base_url,
    admin_headers,
):
    response = requests.get(
        f"{base_url}/accounts/2147483647",
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Account not found"}


def test_get_account_by_id_authorizes_after_global_lookup(
    base_url,
    admin_headers,
):
    company_id: int | None = None
    account_id: int | None = None

    with SessionLocal() as db:
        company = Company(
            name=f"Account access isolation {uuid.uuid4().hex}",
            base_currency="USD",
        )
        db.add(company)
        db.flush()

        account = Account(
            company_id=company.id,
            code="1000",
            name="Unauthorized company account",
            account_type="asset",
            is_active=True,
            is_system=False,
        )
        db.add(account)
        db.commit()
        company_id = company.id
        account_id = account.id

    try:
        response = requests.get(
            f"{base_url}/accounts/{account_id}",
            headers=admin_headers,
        )

        assert response.status_code == 403
    finally:
        with SessionLocal() as db:
            account = db.get(Account, account_id)
            if account is not None:
                db.delete(account)
            company = db.get(Company, company_id)
            if company is not None:
                db.delete(company)
            db.commit()
