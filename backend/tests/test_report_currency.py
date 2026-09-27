# -*- coding: utf-8 -*-
"""Every report totals one currency at a time.

The entry guard ([CUR-1]) stops a single entry mixing riyals and dollars, but
that alone is not enough: a trial balance run across the whole company would
still add a balanced riyal book to a balanced dollar book and print one
meaningless total. These tests pin that each report is computed per currency,
defaults to the company's own, and never lets a figure from the other currency
in -- including the retained earnings the balance sheet pulls from the P&L.
"""
from decimal import Decimal
from uuid import uuid4

import requests


def _account(base_url, headers, company_id, *, name, account_type, currency):
    response = requests.post(
        f"{base_url}/accounts",
        headers=headers,
        json={
            "company_id": company_id,
            "code": f"R{uuid4().hex[:10]}",
            "name": name,
            "account_type": account_type,
            "currency": currency,
            "parent_id": None,
            "description": None,
            "is_active": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _post_sale(base_url, headers, bs, *, cash, revenue, amount):
    created = requests.post(
        f"{base_url}/journal-entries",
        headers=headers,
        json={
            "company_id": bs.company_id,
            "entry_no": f"S-{uuid4().hex[:8]}",
            "entry_date": bs.fiscal_period.start_date.isoformat(),
            "description": "sale",
            "lines": [
                {"account_id": cash["id"], "debit": amount, "credit": "0.00"},
                {"account_id": revenue["id"], "debit": "0.00", "credit": amount},
            ],
        },
    )
    assert created.status_code == 201, created.text
    entry_id = created.json()["id"]
    # Reports only count posted entries, and posting requires a review first.
    for step in ("review", "post"):
        moved = requests.post(
            f"{base_url}/journal-entries/{entry_id}/{step}", headers=headers
        )
        assert moved.status_code == 200, f"{step}: {moved.text}"


def _two_currency_book(base_url, bs):
    """A dollar sale and a riyal sale in one company, each balanced on its own."""
    headers = bs.auth_headers
    usd_cash = _account(base_url, headers, bs.company_id,
                        name="صندوق دولار", account_type="asset", currency="USD")
    usd_rev = _account(base_url, headers, bs.company_id,
                       name="مبيعات دولار", account_type="income", currency="USD")
    yer_cash = _account(base_url, headers, bs.company_id,
                        name="صندوق ريال", account_type="asset", currency="YER")
    yer_rev = _account(base_url, headers, bs.company_id,
                       name="مبيعات ريال", account_type="income", currency="YER")
    _post_sale(base_url, headers, bs, cash=usd_cash, revenue=usd_rev, amount="100.00")
    _post_sale(base_url, headers, bs, cash=yer_cash, revenue=yer_rev, amount="53000.00")
    return {"usd_cash": usd_cash, "yer_cash": yer_cash,
            "usd_rev": usd_rev, "yer_rev": yer_rev}


def _codes(report, key="lines"):
    return {line["account_code"] for line in report[key]}


def test_the_trial_balance_is_one_currency_at_a_time(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    book = _two_currency_book(base_url, bs)

    yer = requests.get(
        f"{base_url}/reports/trial-balance",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id, "currency": "YER"},
    ).json()

    assert yer["currency"] == "YER"
    codes = _codes(yer)
    assert book["yer_cash"]["code"] in codes
    # The dollar accounts are not merely zero here -- they are absent.
    assert book["usd_cash"]["code"] not in codes
    assert book["usd_rev"]["code"] not in codes
    assert yer["is_balanced"] is True


def test_a_report_without_a_currency_is_in_the_companys_own(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    book = _two_currency_book(base_url, bs)
    company = requests.get(
        f"{base_url}/companies/{bs.company_id}", headers=bs.auth_headers
    ).json()
    base = company["base_currency"].upper()

    report = requests.get(
        f"{base_url}/reports/trial-balance",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id},
    ).json()

    assert report["currency"] == base
    other = "YER" if base != "YER" else "USD"
    assert book[f"{other.lower()}_cash"]["code"] not in _codes(report)


def test_profit_and_loss_counts_only_its_own_currency(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    book = _two_currency_book(base_url, bs)

    yer = requests.get(
        f"{base_url}/reports/profit-and-loss",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id, "currency": "YER"},
    ).json()

    assert yer["currency"] == "YER"
    income_codes = {line["account_code"] for line in yer["income_lines"]}
    assert book["yer_rev"]["code"] in income_codes
    assert book["usd_rev"]["code"] not in income_codes
    # 53,000 riyals of income must not have 100 dollars added to it.
    riyal_income = next(
        Decimal(line["amount"]) for line in yer["income_lines"]
        if line["account_code"] == book["yer_rev"]["code"]
    )
    assert riyal_income == Decimal("53000.00")


def test_the_balance_sheet_balances_inside_each_currency(
    base_url, deterministic_accounting_bootstrap
):
    """The trap this closes: the balance sheet computes current-year earnings by
    calling the P&L. If that inner call were not restricted too, the riyal
    balance sheet would set riyal assets against earnings from every currency
    and fail to balance -- or, worse, balance by coincidence."""
    bs = deterministic_accounting_bootstrap
    _two_currency_book(base_url, bs)

    for currency in ("USD", "YER"):
        sheet = requests.get(
            f"{base_url}/reports/balance-sheet",
            headers=bs.auth_headers,
            params={
                "company_id": bs.company_id,
                "currency": currency,
                "as_of_date": bs.fiscal_period.end_date.isoformat(),
            },
        )
        assert sheet.status_code == 200, sheet.text
        body = sheet.json()
        assert body["currency"] == currency
        assert body["is_balanced"] is True, (
            f"{currency} balance sheet does not balance: "
            f"assets {body['total_assets']} vs "
            f"liabilities+equity {body['total_liabilities_and_equity']}"
        )


def test_the_general_ledger_lists_only_one_currencys_accounts(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    book = _two_currency_book(base_url, bs)

    report = requests.get(
        f"{base_url}/reports/general-ledger",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id, "currency": "YER", "account_limit": 500},
    ).json()

    assert report["currency"] == "YER"
    codes = {account["account_code"] for account in report["accounts"]}
    assert book["yer_cash"]["code"] in codes
    assert book["usd_cash"]["code"] not in codes
    # Pagination totals are counted inside the same currency, or a page count
    # would promise accounts the page can never show.
    listing = requests.get(
        f"{base_url}/accounts",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id, "limit": 500},
    ).json()
    riyal_accounts = [a for a in listing["items"] if a["currency"] == "YER"]
    assert report["total_accounts"] == len(riyal_accounts)


def test_the_account_ledger_reports_its_own_currency(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    book = _two_currency_book(base_url, bs)

    ledger = requests.get(
        f"{base_url}/reports/account-ledger",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id, "account_id": book["yer_cash"]["id"]},
    ).json()
    assert ledger["currency"] == "YER"


def test_the_currencies_endpoint_lists_the_base_first(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    _two_currency_book(base_url, bs)

    body = requests.get(
        f"{base_url}/reports/currencies",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id},
    ).json()

    assert body["currencies"][0] == body["base_currency"]
    assert {"USD", "YER"} <= set(body["currencies"])
    assert len(body["currencies"]) == len(set(body["currencies"]))


def test_an_export_follows_the_currency_on_screen(
    base_url, deterministic_accounting_bootstrap
):
    """An exported trial balance that ignored ?currency= would total something
    other than what the user was looking at."""
    bs = deterministic_accounting_bootstrap
    book = _two_currency_book(base_url, bs)

    csv = requests.get(
        f"{base_url}/reports/trial-balance/export.csv",
        headers=bs.auth_headers,
        params={"company_id": bs.company_id, "currency": "YER"},
    )
    assert csv.status_code == 200, csv.text
    text = csv.content.decode("utf-8-sig")
    assert book["yer_cash"]["code"] in text
    assert book["usd_cash"]["code"] not in text
