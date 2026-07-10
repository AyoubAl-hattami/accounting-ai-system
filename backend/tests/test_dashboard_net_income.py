"""
Tests for Dashboard Net Income / Balance Sheet consistency.

Scenario: A posted revenue journal entry (Dr Bank 1000, Cr Sales Revenue 1000)
should produce:
  - P&L: net_profit = 1000
  - Balance Sheet: total_assets = 1000, current_year_earnings = 1000, is_balanced = True
  - Draft entries should NOT affect reports
"""
import os
import requests
import pytest
import uuid
from datetime import date


BASE_URL = os.getenv("ACCOUNTING_TEST_BASE_URL", "http://127.0.0.1:8010")
COMPANY_ID = 3


@pytest.fixture
def admin_headers():
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "admin@example.com",
            "password": "Password123",
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_account_id_by_code(headers, company_id, code):
    """Find an account by its code."""
    resp = requests.get(
        f"{BASE_URL}/accounts?company_id={company_id}&skip=0&limit=100",
        headers=headers,
    )
    assert resp.status_code == 200
    for acc in resp.json()["items"]:
        if acc["code"] == code:
            return acc["id"]
    pytest.fail(f"Account with code {code} not found")


def _create_journal_entry(headers, company_id, bank_id, revenue_id, amount, status="draft"):
    """Create a journal entry with Dr Bank / Cr Sales Revenue."""
    today = date.today().isoformat()
    entry_no = f"TEST-{uuid.uuid4().hex[:8].upper()}"
    payload = {
        "company_id": company_id,
        "entry_no": entry_no,
        "entry_date": today,
        "description": f"Test revenue entry ({status})",
        "source_type": "test",
        "source_id": f"test-{status}",
        "lines": [
            {
                "account_id": bank_id,
                "debit": amount,
                "credit": 0,
                "description": "Bank debit",
            },
            {
                "account_id": revenue_id,
                "debit": 0,
                "credit": amount,
                "description": "Sales revenue credit",
            },
        ],
    }
    resp = requests.post(
        f"{BASE_URL}/journal-entries",
        headers=headers,
        json=payload,
    )
    assert resp.status_code in (200, 201), f"Create entry failed: {resp.text}"
    return resp.json()


def _post_journal_entry(headers, entry_id):
    """Post a draft journal entry."""
    resp = requests.post(
        f"{BASE_URL}/journal-entries/{entry_id}/post",
        headers=headers,
    )
    assert resp.status_code == 200, f"Post entry failed: {resp.text}"
    return resp.json()


def _reverse_journal_entry(headers, entry_id):
    """Reverse a posted journal entry (cleanup)."""
    today = date.today().isoformat()
    resp = requests.post(
        f"{BASE_URL}/journal-entries/{entry_id}/reverse",
        headers=headers,
        json={
            "entry_date": today,
            "description": "Test cleanup reversal",
        },
    )
    return resp


def _void_journal_entry(headers, entry_id):
    """Void a draft journal entry (cleanup)."""
    resp = requests.post(
        f"{BASE_URL}/journal-entries/{entry_id}/void",
        headers=headers,
    )
    return resp


class TestProfitAndLossNetProfit:
    """Test that P&L correctly reports net_profit for posted revenue entries."""

    def test_profit_and_loss_has_net_profit_field(self, admin_headers):
        """Verify the P&L endpoint returns a net_profit field."""
        resp = requests.get(
            f"{BASE_URL}/reports/profit-and-loss?company_id={COMPANY_ID}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "net_profit" in data, (
            f"P&L response missing 'net_profit' field. Keys: {list(data.keys())}"
        )

    def test_posted_revenue_increases_net_profit(self, admin_headers):
        """A posted Dr Bank 1000 / Cr Sales Revenue 1000 should increase net_profit by 1000."""
        bank_id = _get_account_id_by_code(admin_headers, COMPANY_ID, "1110")
        revenue_id = _get_account_id_by_code(admin_headers, COMPANY_ID, "4100")

        # Get baseline P&L
        pl_before = requests.get(
            f"{BASE_URL}/reports/profit-and-loss?company_id={COMPANY_ID}",
            headers=admin_headers,
        ).json()
        baseline_net = float(pl_before["net_profit"])

        # Create and post entry
        entry = _create_journal_entry(admin_headers, COMPANY_ID, bank_id, revenue_id, 1000)
        entry_id = entry["id"]

        try:
            _post_journal_entry(admin_headers, entry_id)

            # Check P&L after posting
            pl_after = requests.get(
                f"{BASE_URL}/reports/profit-and-loss?company_id={COMPANY_ID}",
                headers=admin_headers,
            ).json()

            new_net = float(pl_after["net_profit"])
            assert new_net == baseline_net + 1000, (
                f"Expected net_profit to increase by 1000 "
                f"(baseline={baseline_net}, after={new_net})"
            )
        finally:
            _reverse_journal_entry(admin_headers, entry_id)


class TestBalanceSheetEquation:
    """Test that the balance sheet equation holds after posting revenue."""

    def test_balance_sheet_includes_current_year_earnings(self, admin_headers):
        """Balance sheet must include current_year_earnings and be balanced."""
        bank_id = _get_account_id_by_code(admin_headers, COMPANY_ID, "1110")
        revenue_id = _get_account_id_by_code(admin_headers, COMPANY_ID, "4100")

        # Create and post entry
        entry = _create_journal_entry(admin_headers, COMPANY_ID, bank_id, revenue_id, 1000)
        entry_id = entry["id"]

        try:
            _post_journal_entry(admin_headers, entry_id)

            bs = requests.get(
                f"{BASE_URL}/reports/balance-sheet?company_id={COMPANY_ID}",
                headers=admin_headers,
            ).json()

            total_assets = float(bs["total_assets"])
            total_liabilities = float(bs["total_liabilities"])
            total_equity = float(bs["total_equity"])
            current_year_earnings = float(bs["current_year_earnings"])
            total_le = float(bs["total_liabilities_and_equity"])

            # Accounting equation: Assets = Liabilities + Equity + CYE
            assert total_le == total_liabilities + total_equity + current_year_earnings
            assert total_assets == total_le, (
                f"Balance sheet not balanced: assets={total_assets}, "
                f"L+E+CYE={total_le}"
            )
            assert bs["is_balanced"] is True
        finally:
            _reverse_journal_entry(admin_headers, entry_id)


class TestDraftVsPosted:
    """Test that draft entries do NOT affect reports."""

    def test_draft_entry_does_not_affect_profit_and_loss(self, admin_headers):
        """A draft entry should not change P&L net_profit."""
        bank_id = _get_account_id_by_code(admin_headers, COMPANY_ID, "1110")
        revenue_id = _get_account_id_by_code(admin_headers, COMPANY_ID, "4100")

        # Get baseline
        pl_before = requests.get(
            f"{BASE_URL}/reports/profit-and-loss?company_id={COMPANY_ID}",
            headers=admin_headers,
        ).json()
        baseline_net = float(pl_before["net_profit"])

        # Create draft entry (do NOT post)
        entry = _create_journal_entry(admin_headers, COMPANY_ID, bank_id, revenue_id, 5000)
        entry_id = entry["id"]

        try:
            # Check P&L — should be unchanged
            pl_after = requests.get(
                f"{BASE_URL}/reports/profit-and-loss?company_id={COMPANY_ID}",
                headers=admin_headers,
            ).json()

            new_net = float(pl_after["net_profit"])
            assert new_net == baseline_net, (
                f"Draft entry should not affect net_profit. "
                f"Before={baseline_net}, After={new_net}"
            )
        finally:
            _void_journal_entry(admin_headers, entry_id)

    def test_draft_entry_does_not_affect_balance_sheet(self, admin_headers):
        """A draft entry should not change balance sheet totals."""
        bank_id = _get_account_id_by_code(admin_headers, COMPANY_ID, "1110")
        revenue_id = _get_account_id_by_code(admin_headers, COMPANY_ID, "4100")

        # Get baseline
        bs_before = requests.get(
            f"{BASE_URL}/reports/balance-sheet?company_id={COMPANY_ID}",
            headers=admin_headers,
        ).json()
        baseline_assets = float(bs_before["total_assets"])

        # Create draft entry (do NOT post)
        entry = _create_journal_entry(admin_headers, COMPANY_ID, bank_id, revenue_id, 5000)
        entry_id = entry["id"]

        try:
            bs_after = requests.get(
                f"{BASE_URL}/reports/balance-sheet?company_id={COMPANY_ID}",
                headers=admin_headers,
            ).json()

            new_assets = float(bs_after["total_assets"])
            assert new_assets == baseline_assets, (
                f"Draft entry should not affect total_assets. "
                f"Before={baseline_assets}, After={new_assets}"
            )
        finally:
            _void_journal_entry(admin_headers, entry_id)
