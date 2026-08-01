import uuid
from datetime import timedelta
from decimal import Decimal

import requests

from app.core.database import SessionLocal
from app.modules.accounting.models.audit_log import AuditLog
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.user import User
from app.modules.accounting.services.auth_service import create_user_token


def test_journal_entries_requires_authentication(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = requests.get(
        f"{base_url}/journal-entries?company_id={bs.company_id}",
    )
    assert response.status_code in (401, 403)


def test_journal_entries_work_with_token(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = requests.get(
        f"{base_url}/journal-entries?company_id={bs.company_id}",
        headers=bs.auth_headers,
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
        assert first_entry["company_id"] == bs.company_id


def test_journal_entries_pagination_metadata(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = requests.get(
        f"{base_url}/journal-entries?company_id={bs.company_id}&skip=0&limit=5",
        headers=bs.auth_headers,
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
    base_url, deterministic_accounting_bootstrap, accounting_factory
):
    bs = deterministic_accounting_bootstrap
    bank_id = bs.account_id("1110")
    owner_capital_id = bs.account_id("3100")
    entry_date = bs.fiscal_period.start_date.isoformat()

    marker = uuid.uuid4().hex[:12]
    create_response = requests.post(
        f"{base_url}/journal-entries",
        headers=bs.auth_headers,
        json={
            "company_id": bs.company_id,
            "entry_no": f"CREATOR-{marker}",
            "entry_date": entry_date,
            "description": "creator company isolation",
            "lines": [
                {"account_id": bank_id, "debit": 1, "credit": 0},
                {"account_id": owner_capital_id, "debit": 0, "credit": 1},
            ],
        },
    )
    assert create_response.status_code == 201, create_response.text
    journal = create_response.json()
    assert journal["created_by_user_id"] is not None
    assert journal["creator_name"]

    # Create a foreign company and user via factory; they should not see this entry
    foreign_bs = accounting_factory.create_accounting_bootstrap()
    accounting_factory.db.commit()
    foreign_headers = accounting_factory.auth_headers_for(foreign_bs.user)

    response = requests.get(
        f"{base_url}/journal-entries/{journal['id']}",
        headers=foreign_headers,
    )
    assert response.status_code == 403
    assert set(response.json()) == {"detail"}
    assert journal["creator_name"] not in response.text


def test_journal_read_filter_get_and_error_contracts(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    filtered = requests.get(
        f"{base_url}/journal-entries?company_id={bs.company_id}&status=posted",
        headers=bs.auth_headers,
    )
    assert filtered.status_code == 200
    assert all(entry["status"] == "posted" for entry in filtered.json()["items"])

    invalid = requests.get(
        f"{base_url}/journal-entries?company_id={bs.company_id}&status=invalid",
        headers=bs.auth_headers,
    )
    assert invalid.status_code == 400
    assert invalid.json() == {"detail": "Invalid journal entry status"}

    listing = requests.get(
        f"{base_url}/journal-entries?company_id={bs.company_id}&limit=1",
        headers=bs.auth_headers,
    )
    assert listing.status_code == 200
    if listing.json()["items"]:
        listed = listing.json()["items"][0]
        detail = requests.get(
            f"{base_url}/journal-entries/{listed['id']}",
            headers=bs.auth_headers,
        )
        assert detail.status_code == 200
        assert detail.json() == listed

    missing = requests.get(
        f"{base_url}/journal-entries/2147483647",
        headers=bs.auth_headers,
    )
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Journal entry not found"}


def test_journal_create_response_and_audit_contract(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    bank_id = bs.account_id("1110")
    owner_capital_id = bs.account_id("3100")
    entry_date = bs.fiscal_period.start_date.isoformat()

    marker = uuid.uuid4().hex[:12]
    entry_no = f"CREATE-{marker}"
    response = requests.post(
        f"{base_url}/journal-entries",
        headers=bs.auth_headers,
        json={
            "company_id": bs.company_id,
            "entry_no": f"  {entry_no}  ",
            "entry_date": entry_date,
            "description": " create description unchanged ",
            "source_type": "manual",
            "source_id": marker,
            "lines": [
                {"account_id": bank_id, "debit": 17, "credit": 0, "description": "debit"},
                {"account_id": owner_capital_id, "debit": 0, "credit": 17, "description": "credit"},
            ],
        },
    )

    assert response.status_code == 201, response.text
    journal = response.json()
    assert set(journal) == {
        "id", "company_id", "fiscal_year_id", "fiscal_period_id",
        "entry_no", "entry_date", "description", "status",
        "source_type", "source_id", "created_by_user_id", "creator_name",
        "reversal_of_id", "posted_at", "created_at", "updated_at", "lines",
    }
    assert journal["entry_no"] == entry_no
    assert journal["description"] == " create description unchanged "
    assert journal["status"] == "draft"
    assert journal["source_type"] == "manual"
    assert journal["source_id"] == marker
    assert journal["created_by_user_id"] is not None
    assert journal["creator_name"]
    assert [line["line_no"] for line in journal["lines"]] == [1, 2]
    assert [line["account_id"] for line in journal["lines"]] == [bank_id, owner_capital_id]

    with SessionLocal() as db:
        audits = (
            db.query(AuditLog)
            .filter_by(
                company_id=bs.company_id,
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
        "entry_date": entry_date,
    }


def test_journal_update_contract_fiscal_validation_status_and_audit(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    bank_id = bs.account_id("1110")
    owner_capital_id = bs.account_id("3100")
    entry_date = bs.fiscal_period.start_date.isoformat()
    next_day = (bs.fiscal_period.start_date + timedelta(days=1)).isoformat()

    marker = uuid.uuid4().hex[:12]
    created_response = requests.post(
        f"{base_url}/journal-entries",
        headers=bs.auth_headers,
        json={
            "company_id": bs.company_id,
            "entry_no": f"UPDATE-{marker}",
            "entry_date": entry_date,
            "description": "Before update",
            "source_type": "manual",
            "source_id": "before-source",
            "lines": [
                {"account_id": bank_id, "debit": 23, "credit": 0, "description": "debit unchanged"},
                {"account_id": owner_capital_id, "debit": 0, "credit": 23, "description": "credit unchanged"},
            ],
        },
    )
    assert created_response.status_code == 201, created_response.text
    before = created_response.json()

    updated_response = requests.patch(
        f"{base_url}/journal-entries/{before['id']}",
        headers=bs.auth_headers,
        json={"entry_date": next_day, "description": "After update", "source_type": None},
    )
    assert updated_response.status_code == 200, updated_response.text
    updated = updated_response.json()
    assert set(updated) == set(before)
    assert updated["id"] == before["id"]
    assert updated["entry_no"] == before["entry_no"]
    assert updated["entry_date"] == next_day
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
        headers=bs.auth_headers,
        json={"description": None},
    )
    assert cleared_response.status_code == 200, cleared_response.text
    cleared = cleared_response.json()
    assert cleared["description"] is None
    assert cleared["entry_date"] == next_day
    assert cleared["source_id"] == "before-source"

    with SessionLocal() as db:
        audits = (
            db.query(AuditLog)
            .filter_by(
                company_id=bs.company_id,
                action="update_journal_entry",
                entity_type="journal_entry",
                entity_id=before["id"],
            )
            .all()
        )
    assert len(audits) == 2
    assert all(
        audit.description == f"Updated draft journal entry {before['entry_no']}"
        for audit in audits
    )
    assert all(audit.old_values == {"status": "draft", "entry_no": before["entry_no"]} for audit in audits)
    assert all(audit.new_values == {"status": "draft", "entry_no": before["entry_no"]} for audit in audits)

    invalid_date = requests.patch(
        f"{base_url}/journal-entries/{before['id']}",
        headers=bs.auth_headers,
        json={"entry_date": "2035-01-01"},
    )
    assert invalid_date.status_code == 400
    assert invalid_date.json() == {"detail": "No fiscal year found for this entry date"}

    reviewed = requests.post(
        f"{base_url}/journal-entries/{before['id']}/review",
        headers=bs.auth_headers,
    )
    assert reviewed.status_code == 200, reviewed.text
    protected = requests.patch(
        f"{base_url}/journal-entries/{before['id']}",
        headers=bs.auth_headers,
        json={"description": "Denied"},
    )
    assert protected.status_code == 400
    assert protected.json() == {"detail": "Only draft journal entries can be updated"}

    missing = requests.patch(
        f"{base_url}/journal-entries/2147483647",
        headers=bs.auth_headers,
        json={"description": "Missing"},
    )
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Journal entry not found"}


def test_journal_review_reviewer_role_response_audit_conflict_and_missing(
    base_url, deterministic_accounting_bootstrap, accounting_factory
):
    bs = deterministic_accounting_bootstrap
    bank_id = bs.account_id("1110")
    owner_capital_id = bs.account_id("3100")
    entry_date = bs.fiscal_period.start_date.isoformat()

    marker = uuid.uuid4().hex[:12]
    created_response = requests.post(
        f"{base_url}/journal-entries",
        headers=bs.auth_headers,
        json={
            "company_id": bs.company_id,
            "entry_no": f"REVIEW-{marker}",
            "entry_date": entry_date,
            "description": "Review contract",
            "lines": [
                {"account_id": bank_id, "debit": 29, "credit": 0},
                {"account_id": owner_capital_id, "debit": 0, "credit": 29},
            ],
        },
    )
    assert created_response.status_code == 201, created_response.text
    before = created_response.json()

    # Create a reviewer via factory
    reviewer, _ = accounting_factory.add_member(company=bs.company, role="reviewer", full_name="Journal Reviewer")
    accounting_factory.db.commit()
    reviewer_headers = accounting_factory.auth_headers_for(reviewer)

    response = requests.post(
        f"{base_url}/journal-entries/{before['id']}/review",
        headers=reviewer_headers,
    )
    assert response.status_code == 200, response.text
    reviewed = response.json()
    assert set(reviewed) == set(before)
    assert reviewed["id"] == before["id"]
    assert reviewed["status"] == "reviewed"
    assert reviewed["entry_no"] == before["entry_no"]
    assert reviewed["created_by_user_id"] == before["created_by_user_id"]
    assert reviewed["creator_name"] == before["creator_name"]
    assert [line["account_id"] for line in reviewed["lines"]] == [bank_id, owner_capital_id]

    with SessionLocal() as db:
        audits = (
            db.query(AuditLog)
            .filter_by(
                company_id=bs.company_id,
                action="review_journal_entry",
                entity_type="journal_entry",
                entity_id=before["id"],
            )
            .all()
        )
    assert len(audits) == 1
    audit = audits[0]
    assert audit.actor == reviewer.email
    assert audit.actor_user_id == reviewer.id
    assert audit.actor_email == reviewer.email
    assert audit.actor_name == reviewer.full_name
    assert audit.description == f"Reviewed journal entry {before['entry_no']}"
    assert audit.old_values == {"status": "draft"}
    assert audit.new_values == {"status": "reviewed"}

    repeated = requests.post(
        f"{base_url}/journal-entries/{before['id']}/review",
        headers=reviewer_headers,
    )
    assert repeated.status_code == 409
    assert repeated.json() == {"detail": "Only draft journal entries can be reviewed"}

    missing = requests.post(
        f"{base_url}/journal-entries/2147483647/review",
        headers=reviewer_headers,
    )
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Journal entry not found"}


def test_journal_review_preserves_unbalanced_error(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    bank_id = bs.account_id("1110")
    owner_capital_id = bs.account_id("3100")
    entry_date = bs.fiscal_period.start_date.isoformat()

    marker = uuid.uuid4().hex[:12]
    created_response = requests.post(
        f"{base_url}/journal-entries",
        headers=bs.auth_headers,
        json={
            "company_id": bs.company_id,
            "entry_no": f"UNBAL-{marker}",
            "entry_date": entry_date,
            "lines": [
                {"account_id": bank_id, "debit": 31, "credit": 0},
                {"account_id": owner_capital_id, "debit": 0, "credit": 31},
            ],
        },
    )
    assert created_response.status_code == 201, created_response.text
    journal_id = created_response.json()["id"]

    with SessionLocal() as db:
        credit_line = (
            db.query(JournalLine)
            .filter_by(journal_entry_id=journal_id)
            .filter(JournalLine.credit > 0)
            .one()
        )
        credit_line.credit = Decimal("30.00")
        db.commit()

    response = requests.post(
        f"{base_url}/journal-entries/{journal_id}/review",
        headers=bs.auth_headers,
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Journal entry is not balanced"}
