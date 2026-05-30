import time

import requests


COMPANY_ID = 3
BANK_ACCOUNT_ID = 5
OWNER_CAPITAL_ACCOUNT_ID = 11


def test_opening_balance_review_and_post_workflow(
    base_url,
    admin_headers,
):
    entry_no = f"OB-TEST-{int(time.time())}"

    create_response = requests.post(
        f"{base_url}/journal-entries/opening-balance",
        headers=admin_headers,
        json={
            "company_id": COMPANY_ID,
            "entry_no": entry_no,
            "entry_date": "2026-01-01",
            "description": "Automated opening balance test",
            "lines": [
                {
                    "account_id": BANK_ACCOUNT_ID,
                    "debit": 100,
                    "credit": 0,
                    "description": "Opening bank balance test",
                },
                {
                    "account_id": OWNER_CAPITAL_ACCOUNT_ID,
                    "debit": 0,
                    "credit": 100,
                    "description": "Opening owner capital test",
                },
            ],
        },
    )

    assert create_response.status_code == 201

    created_entry = create_response.json()

    assert created_entry["entry_no"] == entry_no
    assert created_entry["company_id"] == COMPANY_ID
    assert created_entry["status"] == "draft"
    assert created_entry["source_type"] == "opening_balance"
    assert len(created_entry["lines"]) == 2

    journal_entry_id = created_entry["id"]

    review_response = requests.post(
        f"{base_url}/journal-entries/{journal_entry_id}/review",
        headers=admin_headers,
    )

    assert review_response.status_code == 200

    reviewed_entry = review_response.json()

    assert reviewed_entry["id"] == journal_entry_id
    assert reviewed_entry["status"] == "reviewed"

    post_response = requests.post(
        f"{base_url}/journal-entries/{journal_entry_id}/post",
        headers=admin_headers,
    )

    assert post_response.status_code == 200

    posted_entry = post_response.json()

    assert posted_entry["id"] == journal_entry_id
    assert posted_entry["status"] == "posted"
    assert posted_entry["posted_at"] is not None