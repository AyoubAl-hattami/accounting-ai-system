from decimal import Decimal
import os
import uuid

import pytest
import requests


BASE_URL = os.getenv("ACCOUNTING_TEST_BASE_URL", "http://127.0.0.1:8010")


FY1_START = "2024-01-01"
FY1_END = "2024-12-31"
FY2_START = "2025-01-01"
FY2_END = "2025-12-31"
FY2_AS_OF = "2025-12-31"


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _api(method: str, path: str, headers: dict, *, expected=(200,), **kwargs):
    response = requests.request(method, f"{BASE_URL}{path}", headers=headers, **kwargs)
    if response.status_code not in expected:
        pytest.fail(
            f"{method} {path} failed with {response.status_code}: {response.text}"
        )
    return response


def _create_company(headers: dict) -> int:
    name = f"BS Multi Year {uuid.uuid4().hex[:10]}"
    response = _api(
        "POST",
        "/companies",
        headers,
        expected=(201,),
        json={"name": name, "base_currency": "USD"},
    )
    company_id = response.json()["id"]
    _api(
        "POST",
        f"/accounts/seed-defaults?company_id={company_id}",
        headers,
        expected=(200,),
    )
    return company_id


def _create_fiscal_year(headers: dict, company_id: int, name: str, start: str, end: str) -> int:
    response = _api(
        "POST",
        "/fiscal-years",
        headers,
        expected=(201,),
        json={
            "company_id": company_id,
            "name": f"{name}-{uuid.uuid4().hex[:8]}",
            "start_date": start,
            "end_date": end,
            "status": "open",
        },
    )
    return response.json()["id"]


def _create_fiscal_period(
    headers: dict,
    company_id: int,
    fiscal_year_id: int,
    name: str,
    start: str,
    end: str,
) -> int:
    response = _api(
        "POST",
        "/fiscal-periods",
        headers,
        expected=(201,),
        json={
            "company_id": company_id,
            "fiscal_year_id": fiscal_year_id,
            "period_no": 1,
            "name": f"{name}-{uuid.uuid4().hex[:8]}",
            "start_date": start,
            "end_date": end,
            "status": "open",
        },
    )
    return response.json()["id"]


def _setup_company(headers: dict, include_fy1: bool = True, include_fy2: bool = True) -> dict:
    company_id = _create_company(headers)
    if include_fy1:
        fy1_id = _create_fiscal_year(headers, company_id, "FY1", FY1_START, FY1_END)
        _create_fiscal_period(headers, company_id, fy1_id, "FY1 Full", FY1_START, FY1_END)
    if include_fy2:
        fy2_id = _create_fiscal_year(headers, company_id, "FY2", FY2_START, FY2_END)
        _create_fiscal_period(headers, company_id, fy2_id, "FY2 Full", FY2_START, FY2_END)

    accounts_response = _api(
        "GET",
        f"/accounts?company_id={company_id}&skip=0&limit=100",
        headers,
    )
    accounts_by_code = {account["code"]: account for account in accounts_response.json()["items"]}
    return {
        "company_id": company_id,
        "bank_id": accounts_by_code["1110"]["id"],
        "retained_earnings_id": accounts_by_code["3200"]["id"],
        "revenue_id": accounts_by_code["4100"]["id"],
        "expense_id": accounts_by_code["5100"]["id"],
    }


def _create_entry(headers: dict, company_id: int, entry_date: str, lines: list[dict], status: str = "posted") -> dict:
    entry_no = f"BS-{uuid.uuid4().hex[:10].upper()}"
    response = _api(
        "POST",
        "/journal-entries",
        headers,
        expected=(201,),
        json={
            "company_id": company_id,
            "entry_no": entry_no,
            "entry_date": entry_date,
            "description": f"Balance sheet test {entry_no}",
            "source_type": "test",
            "source_id": entry_no,
            "lines": lines,
        },
    )
    entry = response.json()

    if status == "draft":
        return entry
    if status == "reviewed":
        return _api("POST", f"/journal-entries/{entry['id']}/review", headers).json()
    if status == "void":
        return _api("POST", f"/journal-entries/{entry['id']}/void", headers).json()
    if status == "posted":
        return _api("POST", f"/journal-entries/{entry['id']}/post", headers).json()

    raise AssertionError(f"Unsupported journal entry status for test setup: {status}")


def _post_revenue(headers: dict, ctx: dict, entry_date: str, amount: int, status: str = "posted") -> dict:
    return _create_entry(
        headers,
        ctx["company_id"],
        entry_date,
        [
            {"account_id": ctx["bank_id"], "debit": amount, "credit": 0, "description": "Bank debit"},
            {"account_id": ctx["revenue_id"], "debit": 0, "credit": amount, "description": "Revenue credit"},
        ],
        status=status,
    )


def _post_expense(headers: dict, ctx: dict, entry_date: str, amount: int, status: str = "posted") -> dict:
    return _create_entry(
        headers,
        ctx["company_id"],
        entry_date,
        [
            {"account_id": ctx["expense_id"], "debit": amount, "credit": 0, "description": "Expense debit"},
            {"account_id": ctx["bank_id"], "debit": 0, "credit": amount, "description": "Bank credit"},
        ],
        status=status,
    )


def _post_retained_earnings_opening(headers: dict, ctx: dict, entry_date: str, amount: int) -> dict:
    return _create_entry(
        headers,
        ctx["company_id"],
        entry_date,
        [
            {"account_id": ctx["bank_id"], "debit": amount, "credit": 0, "description": "Opening bank"},
            {
                "account_id": ctx["retained_earnings_id"],
                "debit": 0,
                "credit": amount,
                "description": "Opening retained earnings",
            },
        ],
        status="posted",
    )

def _post_manual_closing_entry(headers: dict, ctx: dict, entry_date: str, profit: int) -> dict:
    return _create_entry(
        headers,
        ctx["company_id"],
        entry_date,
        [
            {"account_id": ctx["revenue_id"], "debit": 1000, "credit": 0, "description": "Close revenue"},
            {"account_id": ctx["expense_id"], "debit": 0, "credit": 200, "description": "Close expense"},
            {
                "account_id": ctx["retained_earnings_id"],
                "debit": 0,
                "credit": profit,
                "description": "Close net profit to retained earnings",
            },
        ],
        status="posted",
    )


def _setup_two_year_activity(headers: dict) -> dict:
    ctx = _setup_company(headers)
    _post_revenue(headers, ctx, "2024-06-30", 1000)
    _post_expense(headers, ctx, "2024-07-01", 200)
    _post_revenue(headers, ctx, "2025-06-30", 500)
    _post_expense(headers, ctx, "2025-07-01", 100)
    return ctx


def _balance_sheet(headers: dict, company_id: int, as_of_date: str = FY2_AS_OF) -> dict:
    return _api(
        "GET",
        f"/reports/balance-sheet?company_id={company_id}&as_of_date={as_of_date}",
        headers,
    ).json()


def _profit_and_loss(headers: dict, company_id: int, start_date: str, end_date: str) -> dict:
    return _api(
        "GET",
        (
            f"/reports/profit-and-loss?company_id={company_id}"
            f"&start_date={start_date}&end_date={end_date}"
        ),
        headers,
    ).json()


def _journal_entry_count(headers: dict, company_id: int) -> int:
    response = _api(
        "GET",
        f"/journal-entries?company_id={company_id}&skip=0&limit=1",
        headers,
    )
    return response.json()["total"]


def _assert_two_year_balance_sheet_totals(bs: dict):
    assert _money(bs["equity_accounts_total"]) == Decimal("0.00")
    assert _money(bs["prior_year_earnings"]) == Decimal("800.00")
    assert _money(bs["retained_earnings"]) == Decimal("800.00")
    assert _money(bs["current_year_earnings"]) == Decimal("400.00")
    assert _money(bs["total_assets"]) == Decimal("1200.00")
    assert _money(bs["total_liabilities"]) == Decimal("0.00")
    assert _money(bs["total_equity"]) == Decimal("1200.00")
    assert _money(bs["total_liabilities_and_equity"]) == Decimal("1200.00")
    assert bs["is_balanced"] is True


def test_two_year_balance_sheet_splits_prior_and_current_earnings(admin_headers):
    ctx = _setup_two_year_activity(admin_headers)

    bs = _balance_sheet(admin_headers, ctx["company_id"], FY2_AS_OF)

    _assert_two_year_balance_sheet_totals(bs)


def test_balance_sheet_during_first_year_has_no_prior_year_earnings(admin_headers):
    ctx = _setup_two_year_activity(admin_headers)

    bs = _balance_sheet(admin_headers, ctx["company_id"], FY1_END)

    assert _money(bs["equity_accounts_total"]) == Decimal("0.00")
    assert _money(bs["prior_year_earnings"]) == Decimal("0.00")
    assert _money(bs["retained_earnings"]) == Decimal("0.00")
    assert _money(bs["current_year_earnings"]) == Decimal("800.00")
    assert _money(bs["total_assets"]) == Decimal("800.00")
    assert _money(bs["total_equity"]) == Decimal("800.00")
    assert bs["is_balanced"] is True


def test_unposted_and_void_entries_do_not_affect_balance_sheet_earnings(admin_headers):
    ctx = _setup_two_year_activity(admin_headers)

    _post_revenue(admin_headers, ctx, "2025-08-01", 5000, status="draft")
    _post_revenue(admin_headers, ctx, "2025-08-02", 6000, status="reviewed")
    _post_revenue(admin_headers, ctx, "2025-08-03", 7000, status="void")

    bs = _balance_sheet(admin_headers, ctx["company_id"], FY2_AS_OF)

    _assert_two_year_balance_sheet_totals(bs)


def test_reversal_is_consistent_between_balance_sheet_and_profit_and_loss(admin_headers):
    ctx = _setup_two_year_activity(admin_headers)
    original = _post_revenue(admin_headers, ctx, "2025-09-01", 77)
    reversal_entry_no = f"REV-{uuid.uuid4().hex[:10].upper()}"

    reversal = _api(
        "POST",
        f"/journal-entries/{original['id']}/reverse",
        admin_headers,
        expected=(201,),
        json={
            "entry_no": reversal_entry_no,
            "entry_date": "2025-09-02",
            "description": "Reverse report test revenue",
        },
    ).json()
    _api("POST", f"/journal-entries/{reversal['id']}/post", admin_headers)

    pl = _profit_and_loss(admin_headers, ctx["company_id"], FY2_START, FY2_END)
    bs = _balance_sheet(admin_headers, ctx["company_id"], FY2_AS_OF)

    assert _money(pl["net_profit"]) == Decimal("400.00")
    assert _money(bs["current_year_earnings"]) == Decimal("400.00")
    assert _money(bs["total_assets"]) == Decimal("1200.00")
    assert bs["is_balanced"] is True


def test_company_isolation_for_balance_sheet_earnings(admin_headers):
    company_a = _setup_two_year_activity(admin_headers)
    company_b = _setup_company(admin_headers, include_fy1=False, include_fy2=True)
    _post_revenue(admin_headers, company_b, "2025-10-01", 999)

    bs_a = _balance_sheet(admin_headers, company_a["company_id"], FY2_AS_OF)
    bs_b = _balance_sheet(admin_headers, company_b["company_id"], FY2_AS_OF)

    _assert_two_year_balance_sheet_totals(bs_a)
    assert _money(bs_b["current_year_earnings"]) == Decimal("999.00")
    assert _money(bs_b["total_equity"]) == Decimal("999.00")


def test_missing_fiscal_year_returns_clear_validation_error(admin_headers):
    ctx = _setup_two_year_activity(admin_headers)

    response = requests.get(
        f"{BASE_URL}/reports/balance-sheet"
        f"?company_id={ctx['company_id']}&as_of_date=2026-06-30",
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No fiscal year covers the selected date."


def test_retained_earnings_account_balance_is_separate_from_computed_prior_year_earnings(admin_headers):
    ctx = _setup_company(admin_headers, include_fy1=True, include_fy2=True)
    _post_retained_earnings_opening(admin_headers, ctx, "2025-01-01", 50)

    bs = _balance_sheet(admin_headers, ctx["company_id"], FY2_AS_OF)

    assert _money(bs["equity_accounts_total"]) == Decimal("50.00")
    assert _money(bs["prior_year_earnings"]) == Decimal("0.00")
    assert _money(bs["retained_earnings"]) == Decimal("0.00")
    assert _money(bs["current_year_earnings"]) == Decimal("0.00")
    assert _money(bs["total_assets"]) == Decimal("50.00")
    assert _money(bs["total_equity"]) == Decimal("50.00")
    assert bs["is_balanced"] is True

def test_closing_style_retained_earnings_entry_is_not_double_counted(admin_headers):
    ctx = _setup_company(admin_headers, include_fy1=True, include_fy2=True)
    _post_revenue(admin_headers, ctx, "2024-06-30", 1000)
    _post_expense(admin_headers, ctx, "2024-07-01", 200)
    _post_manual_closing_entry(admin_headers, ctx, "2024-12-31", 800)
    _post_revenue(admin_headers, ctx, "2025-06-30", 500)
    _post_expense(admin_headers, ctx, "2025-07-01", 100)

    bs = _balance_sheet(admin_headers, ctx["company_id"], FY2_AS_OF)

    assert _money(bs["equity_accounts_total"]) == Decimal("800.00")
    assert _money(bs["prior_year_earnings"]) == Decimal("0.00")
    assert _money(bs["retained_earnings"]) == Decimal("0.00")
    assert _money(bs["current_year_earnings"]) == Decimal("400.00")
    assert _money(bs["total_assets"]) == Decimal("1200.00")
    assert _money(bs["total_equity"]) == Decimal("1200.00")
    assert bs["is_balanced"] is True


def test_existing_dashboard_single_year_scenario(admin_headers):
    ctx = _setup_company(admin_headers, include_fy1=False, include_fy2=True)
    _post_revenue(admin_headers, ctx, "2025-05-01", 2000)
    _post_expense(admin_headers, ctx, "2025-05-02", 500)

    bs = _balance_sheet(admin_headers, ctx["company_id"], FY2_AS_OF)

    assert _money(bs["prior_year_earnings"]) == Decimal("0.00")
    assert _money(bs["current_year_earnings"]) == Decimal("1500.00")
    assert _money(bs["total_assets"]) == Decimal("1500.00")
    assert _money(bs["total_liabilities"]) == Decimal("0.00")
    assert _money(bs["total_equity"]) == Decimal("1500.00")
    assert _money(bs["total_liabilities_and_equity"]) == Decimal("1500.00")
    assert bs["is_balanced"] is True


def test_balance_sheet_generation_does_not_write_journal_entries(admin_headers):
    ctx = _setup_two_year_activity(admin_headers)
    count_before = _journal_entry_count(admin_headers, ctx["company_id"])

    bs = _balance_sheet(admin_headers, ctx["company_id"], FY2_AS_OF)

    count_after = _journal_entry_count(admin_headers, ctx["company_id"])
    assert count_after == count_before
    _assert_two_year_balance_sheet_totals(bs)