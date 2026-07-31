import requests


def test_all_reports_work_with_token(base_url, deterministic_accounting_bootstrap):
    company_id = deterministic_accounting_bootstrap.company_id
    bank_account_id = deterministic_accounting_bootstrap.account_id("1110")
    headers = deterministic_accounting_bootstrap.auth_headers

    trial_balance_response = requests.get(
        f"{base_url}/reports/trial-balance?company_id={company_id}",
        headers=headers,
    )

    assert trial_balance_response.status_code == 200

    trial_balance = trial_balance_response.json()

    assert trial_balance["company_id"] == company_id
    assert "total_debit" in trial_balance
    assert "total_credit" in trial_balance
    assert "is_balanced" in trial_balance
    assert isinstance(trial_balance["lines"], list)

    profit_and_loss_response = requests.get(
        f"{base_url}/reports/profit-and-loss?company_id={company_id}",
        headers=headers,
    )

    assert profit_and_loss_response.status_code == 200

    profit_and_loss = profit_and_loss_response.json()

    assert profit_and_loss["company_id"] == company_id
    assert "total_income" in profit_and_loss
    assert "total_expenses" in profit_and_loss
    assert "net_profit" in profit_and_loss
    assert isinstance(profit_and_loss["income_lines"], list)
    assert isinstance(profit_and_loss["expense_lines"], list)

    balance_sheet_response = requests.get(
        f"{base_url}/reports/balance-sheet?company_id={company_id}",
        headers=headers,
    )

    assert balance_sheet_response.status_code == 200

    balance_sheet = balance_sheet_response.json()

    assert balance_sheet["company_id"] == company_id
    assert "total_assets" in balance_sheet
    assert "total_liabilities" in balance_sheet
    assert "total_equity" in balance_sheet
    assert "current_year_earnings" in balance_sheet
    assert "is_balanced" in balance_sheet
    assert isinstance(balance_sheet["asset_lines"], list)
    assert isinstance(balance_sheet["liability_lines"], list)
    assert isinstance(balance_sheet["equity_lines"], list)

    account_ledger_response = requests.get(
        (
            f"{base_url}/reports/account-ledger"
            f"?company_id={company_id}&account_id={bank_account_id}"
        ),
        headers=headers,
    )

    assert account_ledger_response.status_code == 200

    account_ledger = account_ledger_response.json()

    assert account_ledger["company_id"] == company_id
    assert account_ledger["account_id"] == bank_account_id
    assert "opening_balance" in account_ledger
    assert "closing_balance" in account_ledger
    assert isinstance(account_ledger["lines"], list)

    general_ledger_response = requests.get(
        f"{base_url}/reports/general-ledger?company_id={company_id}",
        headers=headers,
    )

    assert general_ledger_response.status_code == 200

    general_ledger = general_ledger_response.json()

    assert general_ledger["company_id"] == company_id
    assert isinstance(general_ledger["accounts"], list)
    assert len(general_ledger["accounts"]) > 0
