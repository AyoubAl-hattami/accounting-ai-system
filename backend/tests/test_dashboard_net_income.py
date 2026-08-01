"""
Tests for Dashboard Net Income / Balance Sheet consistency.

Scenario: A posted revenue journal entry (Dr Bank 1000, Cr Sales Revenue 1000)
should produce:
  - P&L: net_profit = 1000
  - Balance Sheet: total_assets = 1000, current_year_earnings = 1000, total_equity = 1000, is_balanced = True
  - Draft entries should NOT affect reports
"""
import uuid
import requests
from datetime import date


def _create_journal_entry(base_url, headers, company_id, bank_id, revenue_id, amount):
    """Create a draft journal entry with Dr Bank / Cr Sales Revenue."""
    entry_date = date.today().isoformat()
    entry_no = f"TEST-{uuid.uuid4().hex[:8].upper()}"
    resp = requests.post(
        f"{base_url}/journal-entries",
        headers=headers,
        json={
            "company_id": company_id,
            "entry_no": entry_no,
            "entry_date": entry_date,
            "description": "Test revenue entry",
            "lines": [
                {"account_id": bank_id, "debit": amount, "credit": 0},
                {"account_id": revenue_id, "debit": 0, "credit": amount},
            ],
        },
    )
    assert resp.status_code in (200, 201), f"Create entry failed: {resp.text}"
    return resp.json()


def _post_journal_entry(base_url, headers, entry_id):
    review = requests.post(f"{base_url}/journal-entries/{entry_id}/review", headers=headers)
    assert review.status_code == 200, review.text
    response = requests.post(f"{base_url}/journal-entries/{entry_id}/post", headers=headers)
    assert response.status_code == 200, response.text


class TestProfitAndLossNetProfit:
    """P&L correctly reports net_profit for posted revenue entries."""

    def test_profit_and_loss_has_net_profit_field(self, base_url, deterministic_accounting_bootstrap):
        bs = deterministic_accounting_bootstrap
        resp = requests.get(
            f"{base_url}/reports/profit-and-loss?company_id={bs.company_id}",
            headers=bs.auth_headers,
        )
        assert resp.status_code == 200
        assert "net_profit" in resp.json()

    def test_posted_revenue_increases_net_profit(self, base_url, deterministic_accounting_bootstrap):
        bs = deterministic_accounting_bootstrap
        bank_id = bs.account_id("1110")
        revenue_id = bs.account_id("4100")

        entry = _create_journal_entry(base_url, bs.auth_headers, bs.company_id, bank_id, revenue_id, 1000)
        _post_journal_entry(base_url, bs.auth_headers, entry["id"])

        pl = requests.get(
            f"{base_url}/reports/profit-and-loss?company_id={bs.company_id}",
            headers=bs.auth_headers,
        ).json()
        assert float(pl["net_profit"]) == 1000.0


class TestBalanceSheetEquation:
    """Balance sheet equation holds after posting revenue."""

    def test_balance_sheet_includes_current_year_earnings(self, base_url, deterministic_accounting_bootstrap):
        bs = deterministic_accounting_bootstrap
        bank_id = bs.account_id("1110")
        revenue_id = bs.account_id("4100")

        entry = _create_journal_entry(base_url, bs.auth_headers, bs.company_id, bank_id, revenue_id, 1000)
        _post_journal_entry(base_url, bs.auth_headers, entry["id"])

        data = requests.get(
            f"{base_url}/reports/balance-sheet?company_id={bs.company_id}",
            headers=bs.auth_headers,
        ).json()

        total_assets = float(data["total_assets"])
        total_liabilities = float(data["total_liabilities"])
        total_equity = float(data["total_equity"])
        current_year_earnings = float(data["current_year_earnings"])
        total_le = float(data["total_liabilities_and_equity"])

        assert total_le == total_liabilities + total_equity
        assert total_equity >= current_year_earnings
        assert total_assets == total_le
        assert data["is_balanced"] is True


class TestDraftVsPosted:
    """Draft entries must NOT affect reports."""

    def test_draft_entry_does_not_affect_profit_and_loss(self, base_url, deterministic_accounting_bootstrap):
        bs = deterministic_accounting_bootstrap
        bank_id = bs.account_id("1110")
        revenue_id = bs.account_id("4100")

        _create_journal_entry(base_url, bs.auth_headers, bs.company_id, bank_id, revenue_id, 5000)

        pl = requests.get(
            f"{base_url}/reports/profit-and-loss?company_id={bs.company_id}",
            headers=bs.auth_headers,
        ).json()
        assert float(pl["net_profit"]) == 0.0

    def test_draft_entry_does_not_affect_balance_sheet(self, base_url, deterministic_accounting_bootstrap):
        bs = deterministic_accounting_bootstrap
        bank_id = bs.account_id("1110")
        revenue_id = bs.account_id("4100")

        _create_journal_entry(base_url, bs.auth_headers, bs.company_id, bank_id, revenue_id, 5000)

        data = requests.get(
            f"{base_url}/reports/balance-sheet?company_id={bs.company_id}",
            headers=bs.auth_headers,
        ).json()
        assert float(data["total_assets"]) == 0.0
