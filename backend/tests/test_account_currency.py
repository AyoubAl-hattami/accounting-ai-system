# -*- coding: utf-8 -*-
"""One entry, one currency.

A company in Yemen holds riyals and dollars at the same time. Before this the
system had a single currency on the COMPANY and none on the account, so nothing
stopped someone opening a riyal cash box and a dollar cash box -- and the trial
balance then added them together and reported a number that is the sum of two
different things, with no warning anywhere.

The slice these tests pin does not convert between currencies and has no rate
table. It records which unit an account is kept in, and refuses the one
operation that would produce a meaningless figure: an entry whose two sides are
in different units.
"""
from uuid import uuid4

import requests


def _account(base_url, headers, company_id, *, name, currency=None, subtype="cash"):
    payload = {
        "company_id": company_id,
        "code": f"C{uuid4().hex[:10]}",
        "name": name,
        "account_type": "asset",
        "account_subtype": subtype,
        "parent_id": None,
        "description": None,
        "is_active": True,
    }
    if currency is not None:
        payload["currency"] = currency
    response = requests.post(f"{base_url}/accounts", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_an_account_without_a_currency_takes_the_companys_own(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    account = _account(base_url, bs.auth_headers, bs.company_id, name="صندوق")

    company = requests.get(
        f"{base_url}/companies/{bs.company_id}", headers=bs.auth_headers
    ).json()
    assert account["currency"] == company["base_currency"].upper()


def test_a_second_currency_can_be_opened_and_is_stored_upper_case(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    account = _account(
        base_url, bs.auth_headers, bs.company_id, name="صندوق ريال", currency="yer"
    )
    assert account["currency"] == "YER"


def test_a_currency_that_is_not_three_letters_is_refused(
    base_url, deterministic_accounting_bootstrap
):
    bs = deterministic_accounting_bootstrap
    for value in ("12X", "US", "USDD", "$$$"):
        response = requests.post(
            f"{base_url}/accounts",
            headers=bs.auth_headers,
            json={
                "company_id": bs.company_id,
                "code": f"C{uuid4().hex[:10]}",
                "name": "bad",
                "account_type": "asset",
                "currency": value,
                "is_active": True,
            },
        )
        assert response.status_code == 422, f"{value!r} was accepted: {response.text}"


def test_the_currency_cannot_be_changed_after_the_account_exists(
    base_url, deterministic_accounting_bootstrap
):
    """Editing it would re-denominate history without touching a single amount."""
    bs = deterministic_accounting_bootstrap
    account = _account(
        base_url, bs.auth_headers, bs.company_id, name="صندوق ريال", currency="YER"
    )

    response = requests.patch(
        f"{base_url}/accounts/{account['id']}",
        headers=bs.auth_headers,
        json={"currency": "USD"},
    )
    assert response.status_code == 200, response.text

    after = requests.get(
        f"{base_url}/accounts/{account['id']}", headers=bs.auth_headers
    ).json()
    assert after["currency"] == "YER"


def test_a_journal_entry_may_not_mix_currencies(
    base_url, deterministic_accounting_bootstrap
):
    """The whole point: 500 riyals against 500 dollars balances and means nothing."""
    bs = deterministic_accounting_bootstrap
    riyal = _account(base_url, bs.auth_headers, bs.company_id,
                     name="صندوق ريال", currency="YER")
    dollar = _account(base_url, bs.auth_headers, bs.company_id,
                      name="صندوق دولار", currency="USD")

    response = requests.post(
        f"{base_url}/journal-entries",
        headers=bs.auth_headers,
        json={
            "company_id": bs.company_id,
            "entry_no": f"MIX-{uuid4().hex[:8]}",
            "entry_date": bs.fiscal_period.start_date.isoformat(),
            "description": "riyals against dollars",
            "lines": [
                {"account_id": riyal["id"], "debit": "500.00", "credit": "0.00"},
                {"account_id": dollar["id"], "debit": "0.00", "credit": "500.00"},
            ],
        },
    )

    assert response.status_code == 400, response.text
    detail = response.json()["detail"]
    # The message must name both currencies: "it failed" is not actionable when
    # an entry has twenty lines.
    assert "YER" in detail and "USD" in detail
    assert "cannot mix currencies" in detail


def test_an_entry_inside_one_currency_is_accepted(
    base_url, deterministic_accounting_bootstrap
):
    """Guard the guard: the check must refuse mixing, not refuse everything."""
    bs = deterministic_accounting_bootstrap
    riyal = _account(base_url, bs.auth_headers, bs.company_id,
                     name="صندوق ريال", currency="YER")
    other = _account(base_url, bs.auth_headers, bs.company_id,
                     name="بنك ريال", currency="YER", subtype="bank")

    response = requests.post(
        f"{base_url}/journal-entries",
        headers=bs.auth_headers,
        json={
            "company_id": bs.company_id,
            "entry_no": f"OK-{uuid4().hex[:8]}",
            "entry_date": bs.fiscal_period.start_date.isoformat(),
            "description": "both sides in riyals",
            "lines": [
                {"account_id": riyal["id"], "debit": "500.00", "credit": "0.00"},
                {"account_id": other["id"], "debit": "0.00", "credit": "500.00"},
            ],
        },
    )
    assert response.status_code == 201, response.text


def test_a_seeded_chart_is_denominated_in_the_companys_currency(
    base_url, deterministic_accounting_bootstrap
):
    """The seeder used to fall back to the model default, so a riyal company was
    handed a chart of dollar accounts."""
    bs = deterministic_accounting_bootstrap
    company = requests.get(
        f"{base_url}/companies/{bs.company_id}", headers=bs.auth_headers
    ).json()

    response = requests.get(
        f"{base_url}/accounts?company_id={bs.company_id}&limit=200",
        headers=bs.auth_headers,
    )
    assert response.status_code == 200, response.text

    seeded = [a for a in response.json()["items"] if a["is_system"]]
    assert seeded, "no system accounts to check"
    assert {a["currency"] for a in seeded} == {company["base_currency"].upper()}
