import uuid

import requests

from app.core.database import SessionLocal
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.user import User
from app.modules.accounting.services.auth_service import create_user_token


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


def _headers_for_company_role(company_id, role, *, is_active=True):
    with SessionLocal() as db:
        user = User(
            email=f"account_{role}_{uuid.uuid4().hex}@example.com",
            full_name=f"Account {role}",
            hashed_password="not-used-by-this-test",
            is_active=is_active,
            is_superuser=False,
        )
        db.add(user)
        db.flush()
        db.add(
            CompanyUser(
                company_id=company_id,
                user_id=user.id,
                role=role,
                is_active=True,
            )
        )
        db.commit()
        token = create_user_token(user)
    return {"Authorization": f"Bearer {token}"}


def _account_payload(company_id, code, **overrides):
    payload = {
        "company_id": company_id,
        "code": code,
        "name": "Created account",
        "account_type": "asset",
        "parent_id": None,
        "description": None,
        "is_active": True,
        "is_system": False,
    }
    payload.update(overrides)
    return payload


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


def test_create_account_contract_normalization_and_read_pilots(
    base_url,
    admin_headers,
):
    company_id = _create_company(base_url, admin_headers, "Account create")
    code = f"  {uuid.uuid4().hex[:12]}  "
    payload = _account_payload(
        company_id,
        code,
        name="  Normalized name  ",
        description="  unchanged description  ",
        is_active=False,
    )

    response = requests.post(
        f"{base_url}/accounts",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 201, response.text
    account = response.json()
    assert set(account) == {
        "id",
        "company_id",
        "code",
        "name",
        "account_type",
        "parent_id",
        "description",
        "is_active",
        "is_system",
        "created_at",
        "updated_at",
    }
    assert account["company_id"] == company_id
    assert account["code"] == code.strip()
    assert account["name"] == "Normalized name"
    assert account["description"] == "  unchanged description  "
    assert account["is_active"] is False
    assert account["is_system"] is False

    list_response = requests.get(
        f"{base_url}/accounts?company_id={company_id}",
        headers=admin_headers,
    )
    assert list_response.status_code == 200
    assert account["id"] in {
        item["id"] for item in list_response.json()["items"]
    }

    get_response = requests.get(
        f"{base_url}/accounts/{account['id']}",
        headers=admin_headers,
    )
    assert get_response.status_code == 200
    assert get_response.json() == account


def test_create_account_preserves_validation_errors(
    base_url,
    admin_headers,
    superuser_headers,
):
    first_company_id = _create_company(
        base_url,
        admin_headers,
        "Account validation first",
    )
    second_company_id = _create_company(
        base_url,
        admin_headers,
        "Account validation second",
    )
    code = uuid.uuid4().hex[:12]

    created = requests.post(
        f"{base_url}/accounts",
        headers=admin_headers,
        json=_account_payload(first_company_id, code),
    )
    assert created.status_code == 201

    duplicate = requests.post(
        f"{base_url}/accounts",
        headers=admin_headers,
        json=_account_payload(first_company_id, f" {code} "),
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "detail": "Account code already exists for this company"
    }

    same_code_other_company = requests.post(
        f"{base_url}/accounts",
        headers=admin_headers,
        json=_account_payload(second_company_id, code),
    )
    assert same_code_other_company.status_code == 201

    system_account = requests.post(
        f"{base_url}/accounts",
        headers=admin_headers,
        json=_account_payload(
            first_company_id,
            uuid.uuid4().hex[:12],
            is_system=True,
        ),
    )
    assert system_account.status_code == 400
    assert system_account.json() == {
        "detail": (
            "System accounts can only be created by the default account seed"
        )
    }

    missing_parent = requests.post(
        f"{base_url}/accounts",
        headers=admin_headers,
        json=_account_payload(
            first_company_id,
            uuid.uuid4().hex[:12],
            parent_id=2147483647,
        ),
    )
    assert missing_parent.status_code == 404
    assert missing_parent.json() == {"detail": "Parent account not found"}

    cross_company_parent = requests.post(
        f"{base_url}/accounts",
        headers=admin_headers,
        json=_account_payload(
            first_company_id,
            uuid.uuid4().hex[:12],
            parent_id=same_code_other_company.json()["id"],
        ),
    )
    assert cross_company_parent.status_code == 400
    assert cross_company_parent.json() == {
        "detail": "Parent account must belong to the same company"
    }

    missing_company = requests.post(
        f"{base_url}/accounts",
        headers=superuser_headers,
        json=_account_payload(2147483647, uuid.uuid4().hex[:12]),
    )
    assert missing_company.status_code == 404
    assert missing_company.json() == {"detail": "Company not found"}


def test_create_account_role_and_inactive_user_compatibility(
    base_url,
    admin_headers,
):
    company_id = _create_company(base_url, admin_headers, "Account roles")

    accountant_response = requests.post(
        f"{base_url}/accounts",
        headers=_headers_for_company_role(company_id, "accountant"),
        json=_account_payload(company_id, uuid.uuid4().hex[:12]),
    )
    assert accountant_response.status_code == 201

    viewer_response = requests.post(
        f"{base_url}/accounts",
        headers=_headers_for_company_role(company_id, "viewer"),
        json=_account_payload(company_id, uuid.uuid4().hex[:12]),
    )
    assert viewer_response.status_code == 403
    assert viewer_response.json() == {
        "detail": "You do not have permission to perform this action"
    }

    inactive_response = requests.post(
        f"{base_url}/accounts",
        headers=_headers_for_company_role(
            company_id,
            "accountant",
            is_active=False,
        ),
        json=_account_payload(company_id, uuid.uuid4().hex[:12]),
    )
    assert inactive_response.status_code == 403
    assert inactive_response.json() == {"detail": "Inactive user"}
