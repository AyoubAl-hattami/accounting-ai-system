"""
Tests for PDF export endpoints.

Verifies authentication, content-type, content-disposition headers,
PDF signature, and that all five endpoints return valid responses.
"""

import requests


ACCOUNT_ID = 5  # matches DEFAULT_BANK_ACCOUNT_ID in conftest


# ── Trial Balance PDF ──

def test_trial_balance_pdf_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/reports/trial-balance/export.pdf?company_id={default_company_id}",
    )
    assert response.status_code in (401, 403)


def test_trial_balance_pdf_export_works(base_url, admin_headers, default_company_id):
    response = requests.get(
        f"{base_url}/reports/trial-balance/export.pdf?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "trial-balance.pdf" in response.headers["content-disposition"]
    # PDF signature: first 4 bytes are %PDF
    assert response.content[:4] == b"%PDF"


# ── Profit & Loss PDF ──

def test_profit_loss_pdf_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/reports/profit-loss/export.pdf?company_id={default_company_id}",
    )
    assert response.status_code in (401, 403)


def test_profit_loss_pdf_export_works(base_url, admin_headers, default_company_id):
    response = requests.get(
        f"{base_url}/reports/profit-loss/export.pdf?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "profit-and-loss.pdf" in response.headers["content-disposition"]
    assert response.content[:4] == b"%PDF"


# ── Balance Sheet PDF ──

def test_balance_sheet_pdf_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/reports/balance-sheet/export.pdf?company_id={default_company_id}",
    )
    assert response.status_code in (401, 403)


def test_balance_sheet_pdf_export_works(base_url, admin_headers, default_company_id):
    response = requests.get(
        f"{base_url}/reports/balance-sheet/export.pdf?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "balance-sheet.pdf" in response.headers["content-disposition"]
    assert response.content[:4] == b"%PDF"


# ── Account Ledger PDF ──

def test_account_ledger_pdf_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/reports/account-ledger/export.pdf"
        f"?company_id={default_company_id}&account_id={ACCOUNT_ID}",
    )
    assert response.status_code in (401, 403)


def test_account_ledger_pdf_export_works(base_url, admin_headers, default_company_id):
    response = requests.get(
        f"{base_url}/reports/account-ledger/export.pdf"
        f"?company_id={default_company_id}&account_id={ACCOUNT_ID}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "account-ledger.pdf" in response.headers["content-disposition"]
    assert response.content[:4] == b"%PDF"


# ── General Ledger PDF ──

def test_general_ledger_pdf_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/reports/general-ledger/export.pdf?company_id={default_company_id}",
    )
    assert response.status_code in (401, 403)


def test_general_ledger_pdf_export_works(base_url, admin_headers, default_company_id):
    response = requests.get(
        f"{base_url}/reports/general-ledger/export.pdf?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "general-ledger.pdf" in response.headers["content-disposition"]
    assert response.content[:4] == b"%PDF"
