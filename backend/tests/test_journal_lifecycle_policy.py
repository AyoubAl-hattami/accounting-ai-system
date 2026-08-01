"""Live API lifecycle contract tests for journal entries.

Exercises real authorization, fiscal validation, audit logging, and reversal
behavior using factory-created data — no shared seed IDs.
"""
import uuid
import requests


def _entry(base_url, headers, company_id, bank_id, revenue_id, entry_date, status="draft"):
    no = f"LIFE-{uuid.uuid4().hex[:10]}"
    r = requests.post(
        f"{base_url}/journal-entries",
        headers=headers,
        json={
            "company_id": company_id,
            "entry_no": no,
            "entry_date": entry_date,
            "description": "lifecycle integration",
            "lines": [
                {"account_id": bank_id, "debit": 1000, "credit": 0},
                {"account_id": revenue_id, "debit": 0, "credit": 1000},
            ],
        },
    )
    assert r.status_code == 201, r.text
    entry = r.json()
    assert entry["created_by_user_id"] is not None
    assert entry["creator_name"]
    actor_response = requests.get(f"{base_url}/auth/me", headers=headers)
    assert actor_response.status_code == 200, actor_response.text
    actor = actor_response.json()
    assert entry["created_by_user_id"] == actor["id"]
    assert entry["creator_name"] == actor["full_name"]
    if status in {"reviewed", "posted"}:
        r = requests.post(
            f"{base_url}/journal-entries/{entry['id']}/review", headers=headers
        )
        assert r.status_code == 200, r.text
    if status == "posted":
        r = requests.post(
            f"{base_url}/journal-entries/{entry['id']}/post", headers=headers
        )
        assert r.status_code == 200, r.text
    return entry


def test_draft_review_post_and_direct_post_rejected(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    h = bs.auth_headers
    cid = bs.company_id
    bank_id = bs.account_id("1110")
    revenue_id = bs.account_id("4100")
    entry_date = bs.fiscal_period.start_date.isoformat()

    draft = _entry(base_url, h, cid, bank_id, revenue_id, entry_date)
    direct = requests.post(
        f"{base_url}/journal-entries/{draft['id']}/post", headers=h
    )
    assert direct.status_code == 409
    reviewed = requests.post(
        f"{base_url}/journal-entries/{draft['id']}/review", headers=h
    )
    assert reviewed.status_code == 200
    posted = requests.post(
        f"{base_url}/journal-entries/{draft['id']}/post", headers=h
    )
    assert posted.status_code == 200


def test_draft_void_and_posted_void_rejected(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    h = bs.auth_headers
    cid = bs.company_id
    bank_id = bs.account_id("1110")
    revenue_id = bs.account_id("4100")
    entry_date = bs.fiscal_period.start_date.isoformat()

    draft = _entry(base_url, h, cid, bank_id, revenue_id, entry_date)
    voided = requests.post(
        f"{base_url}/journal-entries/{draft['id']}/void", headers=h
    )
    assert voided.status_code == 200

    posted = _entry(base_url, h, cid, bank_id, revenue_id, entry_date, status="posted")
    rejected = requests.post(
        f"{base_url}/journal-entries/{posted['id']}/void", headers=h
    )
    assert rejected.status_code == 409


def test_reviewed_void_rejected(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    h = bs.auth_headers
    cid = bs.company_id
    bank_id = bs.account_id("1110")
    revenue_id = bs.account_id("4100")
    entry_date = bs.fiscal_period.start_date.isoformat()

    entry = _entry(base_url, h, cid, bank_id, revenue_id, entry_date, status="reviewed")
    response = requests.post(
        f"{base_url}/journal-entries/{entry['id']}/void", headers=h
    )
    assert response.status_code == 409


def test_reversal_swaps_lines_and_duplicate_is_409(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    h = bs.auth_headers
    cid = bs.company_id
    bank_id = bs.account_id("1110")
    revenue_id = bs.account_id("4100")
    entry_date = bs.fiscal_period.start_date.isoformat()

    original = _entry(
        base_url, h, cid, bank_id, revenue_id, entry_date, status="posted"
    )
    payload = {
        "entry_no": f"REV-{uuid.uuid4().hex[:10]}",
        "entry_date": entry_date,
    }
    first = requests.post(
        f"{base_url}/journal-entries/{original['id']}/reverse",
        headers=h,
        json=payload,
    )
    assert first.status_code == 201, first.text
    reversal = first.json()
    assert reversal["status"] == "draft"
    assert reversal["reversal_of_id"] == original["id"]
    assert reversal["created_by_user_id"] == original["created_by_user_id"]
    assert reversal["creator_name"] == original["creator_name"]
    assert [(line["debit"], line["credit"]) for line in reversal["lines"]] == [
        ("0.00", "1000.00"),
        ("1000.00", "0.00"),
    ]

    second = requests.post(
        f"{base_url}/journal-entries/{original['id']}/reverse",
        headers=h,
        json={**payload, "entry_no": f"REV2-{uuid.uuid4().hex[:8]}"},
    )
    assert second.status_code == 409

    post_reversal = requests.post(
        f"{base_url}/journal-entries/{reversal['id']}/review", headers=h
    )
    assert post_reversal.status_code == 200
    post_reversal = requests.post(
        f"{base_url}/journal-entries/{reversal['id']}/post", headers=h
    )
    assert post_reversal.status_code == 200

    third = requests.post(
        f"{base_url}/journal-entries/{original['id']}/reverse",
        headers=h,
        json={**payload, "entry_no": f"REV3-{uuid.uuid4().hex[:8]}"},
    )
    assert third.status_code == 409


def test_unauthenticated_direct_mutation_is_denied(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    # Unauthenticated list should be rejected
    unauth_list = requests.get(
        f"{base_url}/journal-entries?company_id={bs.company_id}"
    )
    assert "detail" in unauth_list.json()
    # Unauthenticated mutation should be 401
    response = requests.post(
        f"{base_url}/journal-entries/1/reverse",
        json={"entry_no": "NOAUTH", "entry_date": "2000-01-01"},
    )
    assert response.status_code == 401
