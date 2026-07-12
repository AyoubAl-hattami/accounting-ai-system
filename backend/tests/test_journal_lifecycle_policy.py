"""Live API lifecycle contract tests.

These tests use the existing live-backend fixtures and intentionally exercise
real authorization, fiscal validation, audit logging, and reversal behavior.
"""
import time
import uuid
import requests

COMPANY_ID = 3
BANK_ACCOUNT_ID = 5
REVENUE_ACCOUNT_ID = 11


def _entry(base_url, headers, status="draft"):
    no = f"LIFE-{uuid.uuid4().hex[:10]}"
    r = requests.post(f"{base_url}/journal-entries", headers=headers, json={
        "company_id": COMPANY_ID, "entry_no": no, "entry_date": "2026-01-01",
        "description": "lifecycle integration", "lines": [
            {"account_id": BANK_ACCOUNT_ID, "debit": 1000, "credit": 0},
            {"account_id": REVENUE_ACCOUNT_ID, "debit": 0, "credit": 1000},
        ],
    })
    assert r.status_code == 201, r.text
    entry = r.json()
    if status in {"reviewed", "posted"}:
        r = requests.post(f"{base_url}/journal-entries/{entry['id']}/review", headers=headers)
        assert r.status_code == 200, r.text
    if status == "posted":
        r = requests.post(f"{base_url}/journal-entries/{entry['id']}/post", headers=headers)
        assert r.status_code == 200, r.text
    return entry


def test_draft_review_post_and_direct_post_rejected(base_url, admin_headers):
    draft = _entry(base_url, admin_headers)
    direct = requests.post(f"{base_url}/journal-entries/{draft['id']}/post", headers=admin_headers)
    assert direct.status_code == 409
    reviewed = requests.post(f"{base_url}/journal-entries/{draft['id']}/review", headers=admin_headers)
    assert reviewed.status_code == 200
    posted = requests.post(f"{base_url}/journal-entries/{draft['id']}/post", headers=admin_headers)
    assert posted.status_code == 200


def test_draft_void_and_posted_void_rejected(base_url, admin_headers):
    draft = _entry(base_url, admin_headers)
    voided = requests.post(f"{base_url}/journal-entries/{draft['id']}/void", headers=admin_headers)
    assert voided.status_code == 200
    posted = _entry(base_url, admin_headers, status="posted")
    rejected = requests.post(f"{base_url}/journal-entries/{posted['id']}/void", headers=admin_headers)
    assert rejected.status_code == 409


def test_reviewed_void_rejected(base_url, admin_headers):
    entry = _entry(base_url, admin_headers, status="reviewed")
    response = requests.post(f"{base_url}/journal-entries/{entry['id']}/void", headers=admin_headers)
    assert response.status_code == 409


def test_reversal_swaps_lines_and_duplicate_is_409(base_url, admin_headers):
    original = _entry(base_url, admin_headers, status="posted")
    payload = {"entry_no": f"REV-{uuid.uuid4().hex[:10]}", "entry_date": "2026-01-01"}
    first = requests.post(f"{base_url}/journal-entries/{original['id']}/reverse", headers=admin_headers, json=payload)
    assert first.status_code == 201, first.text
    reversal = first.json()
    assert reversal["status"] == "draft"
    assert reversal["reversal_of_id"] == original["id"]
    assert [(line["debit"], line["credit"]) for line in reversal["lines"]] == [("0.00", "1000.00"), ("1000.00", "0.00")]
    second = requests.post(f"{base_url}/journal-entries/{original['id']}/reverse", headers=admin_headers, json={**payload, "entry_no": f"REV2-{uuid.uuid4().hex[:8]}"})
    assert second.status_code == 409
    post_reversal = requests.post(f"{base_url}/journal-entries/{reversal['id']}/review", headers=admin_headers)
    assert post_reversal.status_code == 200
    post_reversal = requests.post(f"{base_url}/journal-entries/{reversal['id']}/post", headers=admin_headers)
    assert post_reversal.status_code == 200
    third = requests.post(f"{base_url}/journal-entries/{original['id']}/reverse", headers=admin_headers, json={**payload, "entry_no": f"REV3-{uuid.uuid4().hex[:8]}"})
    assert third.status_code == 409


def test_unauthenticated_direct_mutation_is_denied(base_url):
    entry = requests.get(f"{base_url}/journal-entries?company_id={COMPANY_ID}").json()
    assert "detail" in entry
    response = requests.post(f"{base_url}/journal-entries/1/reverse", json={"entry_no": "NOAUTH", "entry_date": "2026-01-01"})
    assert response.status_code == 401