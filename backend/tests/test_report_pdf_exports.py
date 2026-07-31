"""
Tests for PDF export endpoints.

Verifies authentication, content-type, content-disposition headers,
PDF signature, and that all five endpoints return valid responses.
"""

import requests


def test_trial_balance_pdf_requires_authentication(base_url):
    response = requests.get(
        f"{base_url}/reports/trial-balance/export.pdf?company_id=1",
    )
    assert response.status_code in (401, 403)


def test_trial_balance_pdf_export_works(base_url, deterministic_accounting_bootstrap):
    company_id = deterministic_accounting_bootstrap.company_id
    response = requests.get(
        f"{base_url}/reports/trial-balance/export.pdf?company_id={company_id}",
        headers=deterministic_accounting_bootstrap.auth_headers,
    )

    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "trial-balance.pdf" in response.headers["content-disposition"]
    assert response.content[:4] == b"%PDF"


def test_profit_loss_pdf_requires_authentication(base_url):
    response = requests.get(
        f"{base_url}/reports/profit-loss/export.pdf?company_id=1",
    )
    assert response.status_code in (401, 403)


def test_profit_loss_pdf_export_works(base_url, deterministic_accounting_bootstrap):
    company_id = deterministic_accounting_bootstrap.company_id
    response = requests.get(
        f"{base_url}/reports/profit-loss/export.pdf?company_id={company_id}",
        headers=deterministic_accounting_bootstrap.auth_headers,
    )

    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "profit-and-loss.pdf" in response.headers["content-disposition"]
    assert response.content[:4] == b"%PDF"


def test_balance_sheet_pdf_requires_authentication(base_url):
    response = requests.get(
        f"{base_url}/reports/balance-sheet/export.pdf?company_id=1",
    )
    assert response.status_code in (401, 403)


def test_balance_sheet_pdf_export_works(base_url, deterministic_accounting_bootstrap):
    company_id = deterministic_accounting_bootstrap.company_id
    response = requests.get(
        f"{base_url}/reports/balance-sheet/export.pdf?company_id={company_id}",
        headers=deterministic_accounting_bootstrap.auth_headers,
    )

    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "balance-sheet.pdf" in response.headers["content-disposition"]
    assert response.content[:4] == b"%PDF"


def test_account_ledger_pdf_requires_authentication(base_url):
    response = requests.get(
        f"{base_url}/reports/account-ledger/export.pdf?company_id=1&account_id=1",
    )
    assert response.status_code in (401, 403)


def test_account_ledger_pdf_export_works(base_url, deterministic_accounting_bootstrap):
    company_id = deterministic_accounting_bootstrap.company_id
    account_id = deterministic_accounting_bootstrap.account_id("1110")
    response = requests.get(
        f"{base_url}/reports/account-ledger/export.pdf"
        f"?company_id={company_id}&account_id={account_id}",
        headers=deterministic_accounting_bootstrap.auth_headers,
    )

    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "account-ledger.pdf" in response.headers["content-disposition"]
    assert response.content[:4] == b"%PDF"


def test_general_ledger_pdf_requires_authentication(base_url):
    response = requests.get(
        f"{base_url}/reports/general-ledger/export.pdf?company_id=1",
    )
    assert response.status_code in (401, 403)


def test_general_ledger_pdf_export_works(base_url, deterministic_accounting_bootstrap):
    company_id = deterministic_accounting_bootstrap.company_id
    response = requests.get(
        f"{base_url}/reports/general-ledger/export.pdf?company_id={company_id}",
        headers=deterministic_accounting_bootstrap.auth_headers,
    )

    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "general-ledger.pdf" in response.headers["content-disposition"]
    assert response.content[:4] == b"%PDF"
