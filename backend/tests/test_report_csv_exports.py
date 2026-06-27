"""
Tests for CSV export endpoints.

Verifies authentication, content-type, content-disposition headers,
and that CSV output contains the expected column headers.
"""

import requests


COMPANY_ID = 3
# Use any valid account_id from the seeded chart of accounts
ACCOUNT_ID = 5


# ── Trial Balance CSV ──

def test_trial_balance_csv_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/reports/trial-balance/export.csv?company_id={default_company_id}",
    )
    assert response.status_code in (401, 403)


def test_trial_balance_csv_export_works(base_url, admin_headers, default_company_id):
    response = requests.get(
        f"{base_url}/reports/trial-balance/export.csv?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "trial-balance.csv" in response.headers["content-disposition"]

    text = response.text
    assert "Account Code" in text
    assert "Account Name" in text
    assert "Account Type" in text
    assert "Debit" in text
    assert "Credit" in text


# ── Profit & Loss CSV ──

def test_profit_loss_csv_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/reports/profit-loss/export.csv?company_id={default_company_id}",
    )
    assert response.status_code in (401, 403)


def test_profit_loss_csv_export_works(base_url, admin_headers, default_company_id):
    response = requests.get(
        f"{base_url}/reports/profit-loss/export.csv?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "profit-and-loss.csv" in response.headers["content-disposition"]

    text = response.text
    assert "Section" in text
    assert "Account Code" in text
    assert "Account Name" in text
    assert "Amount" in text
    assert "Total Revenue" in text
    assert "Total Expenses" in text
    assert "Net Income" in text


# ── Balance Sheet CSV ──

def test_balance_sheet_csv_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/reports/balance-sheet/export.csv?company_id={default_company_id}",
    )
    assert response.status_code in (401, 403)


def test_balance_sheet_csv_export_works(base_url, admin_headers, default_company_id):
    response = requests.get(
        f"{base_url}/reports/balance-sheet/export.csv?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "balance-sheet.csv" in response.headers["content-disposition"]

    text = response.text
    assert "Section" in text
    assert "Account Code" in text
    assert "Account Name" in text
    assert "Amount" in text
    assert "Total Assets" in text
    assert "Total Liabilities" in text


# ── Account Ledger CSV ──

def test_account_ledger_csv_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/reports/account-ledger/export.csv"
        f"?company_id={default_company_id}&account_id={ACCOUNT_ID}",
    )
    assert response.status_code in (401, 403)


def test_account_ledger_csv_export_works(base_url, admin_headers, default_company_id):
    response = requests.get(
        f"{base_url}/reports/account-ledger/export.csv"
        f"?company_id={default_company_id}&account_id={ACCOUNT_ID}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "account-ledger.csv" in response.headers["content-disposition"]

    text = response.text
    assert "Date" in text
    assert "Entry No" in text
    assert "Description" in text
    assert "Debit" in text
    assert "Credit" in text
    assert "Balance" in text


# ── General Ledger CSV ──

def test_general_ledger_csv_requires_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/reports/general-ledger/export.csv?company_id={default_company_id}",
    )
    assert response.status_code in (401, 403)


def test_general_ledger_csv_export_works(base_url, admin_headers, default_company_id):
    response = requests.get(
        f"{base_url}/reports/general-ledger/export.csv?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "general-ledger.csv" in response.headers["content-disposition"]

    text = response.text
    assert "Account Code" in text
    assert "Account Name" in text
    assert "Date" in text
    assert "Entry No" in text
    assert "Description" in text
    assert "Debit" in text
    assert "Credit" in text
    assert "Balance" in text
