import uuid
from decimal import Decimal

import requests

from app.core.database import SessionLocal
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.audit_log import AuditLog
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

def test_journal_read_filter_get_and_error_contracts(
    base_url,
    admin_headers,
    default_company_id,
):
    filtered = requests.get(
        f"{base_url}/journal-entries?company_id={default_company_id}&status=posted",
        headers=admin_headers,
    )
    assert filtered.status_code == 200
    assert all(entry["status"] == "posted" for entry in filtered.json()["items"])

    invalid = requests.get(
        f"{base_url}/journal-entries?company_id={default_company_id}&status=invalid",
        headers=admin_headers,
    )
    assert invalid.status_code == 400
    assert invalid.json() == {"detail": "Invalid journal entry status"}

    listing = requests.get(
        f"{base_url}/journal-entries?company_id={default_company_id}&limit=1",
        headers=admin_headers,
    )
    assert listing.status_code == 200
    if listing.json()["items"]:
        listed = listing.json()["items"][0]
        detail = requests.get(
            f"{base_url}/journal-entries/{listed['id']}",
            headers=admin_headers,
        )
        assert detail.status_code == 200
        assert detail.json() == listed

    missing = requests.get(
        f"{base_url}/journal-entries/2147483647",
        headers=admin_headers,
    )
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Journal entry not found"}

def test_journal_create_response_and_audit_contract(
    base_url,
    admin_headers,
    default_company_id,
    default_bank_account_id,
    default_owner_capital_account_id,
):
    marker = uuid.uuid4().hex[:12]
    entry_no = f"CREATE-{marker}"
    response = requests.post(
        f"{base_url}/journal-entries",
        headers=admin_headers,
        json={
            "company_id": default_company_id,
            "entry_no": f"  {entry_no}  ",
            "entry_date": "2026-01-01",
            "description": " create description unchanged ",
            "source_type": "manual",
            "source_id": marker,
            "lines": [
                {
                    "account_id": default_bank_account_id,
                    "debit": 17,
                    "credit": 0,
                    "description": "debit",
                },
                {
                    "account_id": default_owner_capital_account_id,
                    "debit": 0,
                    "credit": 17,
                    "description": "credit",
                },
            ],
        },
    )

    assert response.status_code == 201, response.text
    journal = response.json()
    assert set(journal) == {
        "id",
        "company_id",
        "fiscal_year_id",
        "fiscal_period_id",
        "entry_no",
        "entry_date",
        "description",
        "status",
        "source_type",
        "source_id",
        "created_by_user_id",
        "creator_name",
        "reversal_of_id",
        "posted_at",
        "created_at",
        "updated_at",
        "lines",
    }
    assert journal["entry_no"] == entry_no
    assert journal["description"] == " create description unchanged "
    assert journal["status"] == "draft"
    assert journal["source_type"] == "manual"
    assert journal["source_id"] == marker
    assert journal["created_by_user_id"] is not None
    assert journal["creator_name"]
    assert [line["line_no"] for line in journal["lines"]] == [1, 2]
    assert [line["account_id"] for line in journal["lines"]] == [
        default_bank_account_id,
        default_owner_capital_account_id,
    ]

    with SessionLocal() as db:
        audits = (
            db.query(AuditLog)
            .filter_by(
                company_id=default_company_id,
                action="create_journal_entry",
                entity_type="journal_entry",
                entity_id=journal["id"],
            )
            .all()
        )
    assert len(audits) == 1
    audit = audits[0]
    assert audit.description == f"Created journal entry {entry_no}"
    assert audit.new_values == {
        "entry_no": entry_no,
        "status": "draft",
        "entry_date": "2026-01-01",
    }

def test_journal_update_contract_fiscal_validation_status_and_audit(
    base_url,
    admin_headers,
    default_company_id,
    default_bank_account_id,
    default_owner_capital_account_id,
):
    marker = uuid.uuid4().hex[:12]
    created_response = requests.post(
        f"{base_url}/journal-entries",
        headers=admin_headers,
        json={
            "company_id": default_company_id,
            "entry_no": f"UPDATE-{marker}",
            "entry_date": "2026-01-01",
            "description": "Before update",
            "source_type": "manual",
            "source_id": "before-source",
            "lines": [
                {
                    "account_id": default_bank_account_id,
                    "debit": 23,
                    "credit": 0,
                    "description": "debit unchanged",
                },
                {
                    "account_id": default_owner_capital_account_id,
                    "debit": 0,
                    "credit": 23,
                    "description": "credit unchanged",
                },
            ],
        },
    )
    assert created_response.status_code == 201, created_response.text
    before = created_response.json()

    updated_response = requests.patch(
        f"{base_url}/journal-entries/{before['id']}",
        headers=admin_headers,
        json={
            "entry_date": "2026-01-02",
            "description": "After update",
            "source_type": None,
        },
    )

    assert updated_response.status_code == 200, updated_response.text
    updated = updated_response.json()
    assert set(updated) == set(before)
    assert updated["id"] == before["id"]
    assert updated["entry_no"] == before["entry_no"]
    assert updated["entry_date"] == "2026-01-02"
    assert updated["description"] == "After update"
    assert updated["source_type"] is None
    assert updated["source_id"] == "before-source"
    assert updated["created_by_user_id"] == before["created_by_user_id"]
    assert updated["creator_name"] == before["creator_name"]
    assert [
        (line["account_id"], line["line_no"], Decimal(line["debit"]), Decimal(line["credit"]))
        for line in updated["lines"]
    ] == [
        (line["account_id"], line["line_no"], Decimal(line["debit"]), Decimal(line["credit"]))
        for line in before["lines"]
    ]

    cleared_response = requests.patch(
        f"{base_url}/journal-entries/{before['id']}",
        headers=admin_headers,
        json={"description": None},
    )
    assert cleared_response.status_code == 200, cleared_response.text
    cleared = cleared_response.json()
    assert cleared["description"] is None
    assert cleared["entry_date"] == "2026-01-02"
    assert cleared["source_id"] == "before-source"

    with SessionLocal() as db:
        audits = (
            db.query(AuditLog)
            .filter_by(
                company_id=default_company_id,
                action="update_journal_entry",
                entity_type="journal_entry",
                entity_id=before["id"],
            )
            .all()
        )
    assert len(audits) == 2
    assert all(
        audit.description
        == f"Updated draft journal entry {before['entry_no']}"
        for audit in audits
    )
    assert all(
        audit.old_values == {"status": "draft", "entry_no": before["entry_no"]}
        for audit in audits
    )
    assert all(
        audit.new_values == {"status": "draft", "entry_no": before["entry_no"]}
        for audit in audits
    )

    invalid_date = requests.patch(
        f"{base_url}/journal-entries/{before['id']}",
        headers=admin_headers,
        json={"entry_date": "2035-01-01"},
    )
    assert invalid_date.status_code == 400
    assert invalid_date.json() == {
        "detail": "No fiscal year found for this entry date"
    }

    reviewed = requests.post(
        f"{base_url}/journal-entries/{before['id']}/review",
        headers=admin_headers,
    )
    assert reviewed.status_code == 200, reviewed.text
    protected = requests.patch(
        f"{base_url}/journal-entries/{before['id']}",
        headers=admin_headers,
        json={"description": "Denied"},
    )
    assert protected.status_code == 400
    assert protected.json() == {
        "detail": "Only draft journal entries can be updated"
    }

    missing = requests.patch(
        f"{base_url}/journal-entries/2147483647",
        headers=admin_headers,
        json={"description": "Missing"},
    )
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Journal entry not found"}
