"""Opening balance review-and-post workflow integration test."""
import time

import requests


def test_opening_balance_review_and_post_workflow(
    base_url,
    deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    company_id = bs.company_id
    bank_id = bs.account_id("1110")
    owner_capital_id = bs.account_id("3100")

    entry_no = f"OB-TEST-{int(time.time())}"

    create_response = requests.post(
        f"{base_url}/journal-entries/opening-balance",
        headers=bs.auth_headers,
        json={
            "company_id": company_id,
            "entry_no": entry_no,
            "entry_date": bs.fiscal_period.start_date.isoformat(),
            "description": "Automated opening balance test",
            "lines": [
                {
                    "account_id": bank_id,
                    "debit": 100,
                    "credit": 0,
                    "description": "Opening bank balance test",
                },
                {
                    "account_id": owner_capital_id,
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
    assert created_entry["company_id"] == company_id
    assert created_entry["status"] == "draft"
    assert created_entry["source_type"] == "opening_balance"
    assert len(created_entry["lines"]) == 2

    journal_entry_id = created_entry["id"]

    review_response = requests.post(
        f"{base_url}/journal-entries/{journal_entry_id}/review",
        headers=bs.auth_headers,
    )
    assert review_response.status_code == 200
    assert review_response.json()["status"] == "reviewed"

    post_response = requests.post(
        f"{base_url}/journal-entries/{journal_entry_id}/post",
        headers=bs.auth_headers,
    )
    assert post_response.status_code == 200
    posted_entry = post_response.json()
    assert posted_entry["id"] == journal_entry_id
    assert posted_entry["status"] == "posted"
    assert posted_entry["posted_at"] is not None
