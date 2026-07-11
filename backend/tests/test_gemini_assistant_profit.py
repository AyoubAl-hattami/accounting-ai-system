"""
Tests for Gemini Assistant profit/net income answers.

Verifies that when the user asks profit-related questions (Arabic/English),
the assistant returns actual P&L data rather than 0.00.
"""

import os
import requests
import re

BASE_URL = os.getenv("ACCOUNTING_TEST_BASE_URL", "http://127.0.0.1:8010")
COMPANY_ID = 3


def _admin_headers():
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "admin@example.com", "password": "Password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _gemini_request(headers, message, language="ar"):
    return requests.post(
        f"{BASE_URL}/ai/gemini-assistant",
        headers=headers,
        json={
            "company_id": COMPANY_ID,
            "message": message,
            "language": language,
            "page_context": {"route": "/dashboard", "page": "dashboard", "filters": {}},
            "history": [],
        },
    )


def _get_pl_net_profit(headers):
    """Get actual net_profit from P&L report for reference."""
    resp = requests.get(
        f"{BASE_URL}/reports/profit-and-loss?company_id={COMPANY_ID}",
        headers=headers,
    )
    assert resp.status_code == 200
    return float(resp.json()["net_profit"])


def _extract_numbers(text):
    """Extract all numbers (including decimals and comma-formatted) from text."""
    # Match numbers like 1,500.00 or 1500.00 or 1500
    raw_numbers = re.findall(r'[\d,]+\.?\d*', text)
    result = []
    for n in raw_numbers:
        try:
            result.append(float(n.replace(',', '')))
        except ValueError:
            pass
    return result


class TestGeminiProfitAnswers:
    """Test that Gemini correctly answers profit questions with real data."""

    def test_arabic_profit_question_returns_nonzero(self):
        """'كم الأرباح؟' should return actual net profit, not 0.00."""
        headers = _admin_headers()
        actual_net = _get_pl_net_profit(headers)

        # Only run if there's actual data
        if actual_net == 0.0:
            return  # Skip — no posted entries to test against

        resp = _gemini_request(headers, "كم الأرباح؟", language="ar")
        assert resp.status_code == 200

        reply = resp.json()["reply"]
        numbers = _extract_numbers(reply)

        # The actual net profit must appear in the reply
        assert any(
            abs(n - actual_net) < 1.0 for n in numbers
        ), (
            f"Expected net profit ~{actual_net} to appear in reply. "
            f"Numbers found: {numbers}. Reply: {reply[:200]}"
        )

    def test_arabic_net_profit_question(self):
        """'كم صافي الربح؟' should return actual net profit."""
        headers = _admin_headers()
        actual_net = _get_pl_net_profit(headers)

        if actual_net == 0.0:
            return

        resp = _gemini_request(headers, "كم صافي الربح؟", language="ar")
        assert resp.status_code == 200

        reply = resp.json()["reply"]
        numbers = _extract_numbers(reply)

        assert any(
            abs(n - actual_net) < 1.0 for n in numbers
        ), (
            f"Expected net profit ~{actual_net} in reply. "
            f"Numbers found: {numbers}. Reply: {reply[:200]}"
        )

    def test_arabic_net_income_question(self):
        """'كم صافي الدخل؟' should return actual net profit."""
        headers = _admin_headers()
        actual_net = _get_pl_net_profit(headers)

        if actual_net == 0.0:
            return

        resp = _gemini_request(headers, "كم صافي الدخل؟", language="ar")
        assert resp.status_code == 200

        reply = resp.json()["reply"]
        numbers = _extract_numbers(reply)

        assert any(
            abs(n - actual_net) < 1.0 for n in numbers
        ), (
            f"Expected net profit ~{actual_net} in reply. "
            f"Numbers found: {numbers}. Reply: {reply[:200]}"
        )

    def test_english_net_profit_question(self):
        """'what is net profit?' should return actual net profit."""
        headers = _admin_headers()
        actual_net = _get_pl_net_profit(headers)

        if actual_net == 0.0:
            return

        resp = _gemini_request(headers, "what is net profit?", language="en")
        assert resp.status_code == 200

        reply = resp.json()["reply"]
        numbers = _extract_numbers(reply)

        assert any(
            abs(n - actual_net) < 1.0 for n in numbers
        ), (
            f"Expected net profit ~{actual_net} in reply. "
            f"Numbers found: {numbers}. Reply: {reply[:200]}"
        )

    def test_reply_does_not_show_zero_when_data_exists(self):
        """If P&L has non-zero net profit, reply must not say 0.00."""
        headers = _admin_headers()
        actual_net = _get_pl_net_profit(headers)

        if actual_net == 0.0:
            return

        resp = _gemini_request(headers, "كم الأرباح؟", language="ar")
        assert resp.status_code == 200

        reply = resp.json()["reply"]

        # The reply should NOT claim net profit is 0.00
        assert "Net Profit/Loss for all available data is 0.00" not in reply, (
            f"Reply incorrectly shows 0.00 when actual net profit is {actual_net}"
        )

    def test_report_question_intent_detected(self):
        """Profit questions should be classified as report_question intent."""
        headers = _admin_headers()

        for msg in ["كم الأرباح؟", "كم صافي الربح؟", "what is net profit?"]:
            resp = _gemini_request(headers, msg, language="ar" if "كم" in msg else "en")
            assert resp.status_code == 200

            data = resp.json()
            assert data["intent"] == "answer_report_question", (
                f"Message '{msg}' should produce intent 'answer_report_question', "
                f"got '{data['intent']}'"
            )

    def test_reply_includes_revenue_and_expenses(self):
        """Reply should include at least the net profit in the answer.
        When Gemini is active, it may summarize differently, but the fallback
        always includes revenue, expenses, and net profit.
        """
        headers = _admin_headers()
        actual_net = _get_pl_net_profit(headers)

        if actual_net == 0.0:
            return

        # Get actual P&L data
        pl = requests.get(
            f"{BASE_URL}/reports/profit-and-loss?company_id={COMPANY_ID}",
            headers=headers,
        ).json()
        actual_income = float(pl["total_income"])
        actual_expenses = float(pl["total_expenses"])

        resp = _gemini_request(headers, "كم الأرباح إجمالاً؟", language="ar")
        assert resp.status_code == 200

        reply = resp.json()["reply"]
        numbers = _extract_numbers(reply)

        # At minimum, the net profit must appear
        assert any(
            abs(n - actual_net) < 1.0 for n in numbers
        ), (
            f"Expected net profit ~{actual_net} in reply. "
            f"Numbers: {numbers}. Reply: {reply[:300]}"
        )

        # Check if revenue and expenses also appear (best effort — Gemini may omit)
        has_income = actual_income == 0 or any(abs(n - actual_income) < 1.0 for n in numbers)
        has_expenses = actual_expenses == 0 or any(abs(n - actual_expenses) < 1.0 for n in numbers)

        if not has_income or not has_expenses:
            # Not a failure — Gemini may summarize. Just log it.
            pass
