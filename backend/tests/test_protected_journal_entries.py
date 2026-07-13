import uuid

import requests

from app.core.database import SessionLocal
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.user import User
from app.modules.accounting.services.auth_service import create_user_token


def test_journal_entries_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/journal-entries?company_id={default_company_id}",
    )

    assert response.status_code in (401, 403)


def test_journal_entries_work_with_token(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/journal-entries?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data

    assert isinstance(data["items"], list)
    assert data["total"] >= len(data["items"])

    if len(data["items"]) > 0:
        first_entry = data["items"][0]

        assert "id" in first_entry
        assert "company_id" in first_entry
        assert "entry_no" in first_entry
        assert "status" in first_entry
        assert "created_by_user_id" in first_entry
        assert "creator_name" in first_entry
        assert first_entry["company_id"] == default_company_id


def test_journal_entries_pagination_metadata(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        (
            f"{base_url}/journal-entries"
            f"?company_id={default_company_id}&skip=0&limit=5"
        ),
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) <= 5
    assert data["total"] >= len(data["items"])
    assert data["skip"] == 0
    assert data["limit"] == 5

def test_historical_journal_without_creator_has_safe_fallback():
    journal = JournalEntry()
    assert journal.creator_name is None


def test_journal_creator_is_not_exposed_across_companies(
    base_url,
    admin_headers,
    default_company_id,
    default_bank_account_id,
    default_owner_capital_account_id,
):
    marker = uuid.uuid4().hex[:12]
    create_response = requests.post(
        f"{base_url}/journal-entries",
        headers=admin_headers,
        json={
            "company_id": default_company_id,
            "entry_no": f"CREATOR-{marker}",
            "entry_date": "2026-01-01",
            "description": "creator company isolation",
            "lines": [
                {"account_id": default_bank_account_id, "debit": 1, "credit": 0},
                {"account_id": default_owner_capital_account_id, "debit": 0, "credit": 1},
            ],
        },
    )
    assert create_response.status_code == 201, create_response.text
    journal = create_response.json()
    assert journal["created_by_user_id"] is not None
    assert journal["creator_name"]

    with SessionLocal() as db:
        foreign_company = Company(name=f"Creator Isolation {marker}", base_currency="USD")
        foreign_user = User(
            email=f"creator-isolation-{marker}@example.test",
            full_name="Foreign Company User",
            hashed_password="not-used-by-this-test",
            is_active=True,
            is_superuser=False,
        )
        db.add_all([foreign_company, foreign_user])
        db.flush()
        membership = CompanyUser(
            company_id=foreign_company.id,
            user_id=foreign_user.id,
            role="viewer",
            is_active=True,
        )
        db.add(membership)
        db.commit()
        foreign_company_id = foreign_company.id
        foreign_user_id = foreign_user.id
        foreign_headers = {"Authorization": f"Bearer {create_user_token(foreign_user)}"}

    try:
        response = requests.get(
            f"{base_url}/journal-entries/{journal['id']}",
            headers=foreign_headers,
        )
        assert response.status_code == 403
        assert set(response.json()) == {"detail"}
        assert journal["creator_name"] not in response.text
    finally:
        with SessionLocal() as db:
            membership = db.query(CompanyUser).filter_by(
                company_id=foreign_company_id,
                user_id=foreign_user_id,
            ).one()
            db.delete(membership)
            db.flush()
            db.delete(db.get(User, foreign_user_id))
            db.delete(db.get(Company, foreign_company_id))
            db.commit()