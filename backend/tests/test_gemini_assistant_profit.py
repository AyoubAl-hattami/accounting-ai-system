"""
Tests for Gemini Assistant profit/net income answers.

Verifies that when the user asks profit-related questions (Arabic/English),
the assistant returns actual P&L data rather than 0.00.
"""

import uuid
import requests
import re
from datetime import datetime, timezone


def _gemini_request(base_url, headers, company_id, message, language="ar"):
    return requests.post(
        f"{base_url}/ai/gemini-assistant",
        headers=headers,
        json={
            "company_id": company_id,
            "message": message,
            "language": language,
            "page_context": {"route": "/dashboard", "page": "dashboard", "filters": {}},
            "history": [],
        },
    )


def _get_pl_net_profit(base_url, headers, company_id):
    resp = requests.get(
        f"{base_url}/reports/profit-and-loss?company_id={company_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _seed_pl_data(base_url, headers, bs):
    """Seed revenue 2000 and expense 500 so net_profit == 1500."""
    bank_id = bs.account_id("1110")
    revenue_id = bs.account_id("4100")
    expense_id = bs.account_id("5100")
    entry_date = bs.fiscal_period.start_date.isoformat()

    def _create_and_post(debit_id, credit_id, amount, desc):
        r = requests.post(
            f"{base_url}/journal-entries",
            headers=headers,
            json={
                "company_id": bs.company_id,
                "entry_no": f"SEED-{uuid.uuid4().hex[:8].upper()}",
                "entry_date": entry_date,
                "description": desc,
                "source_type": "test",
                "source_id": f"seed-{uuid.uuid4().hex[:8]}",
                "lines": [
                    {"account_id": debit_id, "debit": amount, "credit": 0, "description": desc},
                    {"account_id": credit_id, "debit": 0, "credit": amount, "description": desc},
                ],
            },
        )
        assert r.status_code == 201, r.text
        eid = r.json()["id"]
        rev = requests.post(f"{base_url}/journal-entries/{eid}/review", headers=headers)
        assert rev.status_code == 200, rev.text
        post = requests.post(f"{base_url}/journal-entries/{eid}/post", headers=headers)
        assert post.status_code == 200, post.text

    _create_and_post(bank_id, revenue_id, 2000, "Seeded revenue")
    _create_and_post(expense_id, bank_id, 500, "Seeded expense")


def _extract_numbers(text):
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

    def test_arabic_profit_question_returns_nonzero(self, base_url, deterministic_accounting_bootstrap):
        """'كم الأرباح؟' should return actual net profit, not 0.00."""
        bs = deterministic_accounting_bootstrap
        _seed_pl_data(base_url, bs.auth_headers, bs)
        pl = _get_pl_net_profit(base_url, bs.auth_headers, bs.company_id)
        actual_net = float(pl["net_profit"])

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "كم الأرباح؟", language="ar")
        assert resp.status_code == 200

        reply = resp.json()["reply"]
        numbers = _extract_numbers(reply)
        assert any(abs(n - actual_net) < 1.0 for n in numbers), (
            f"Expected net profit ~{actual_net} to appear in reply. "
            f"Numbers found: {numbers}. Reply: {reply[:200]}"
        )

    def test_arabic_net_profit_question(self, base_url, deterministic_accounting_bootstrap):
        """'كم صافي الربح؟' should return actual net profit."""
        bs = deterministic_accounting_bootstrap
        _seed_pl_data(base_url, bs.auth_headers, bs)
        actual_net = float(_get_pl_net_profit(base_url, bs.auth_headers, bs.company_id)["net_profit"])

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "كم صافي الربح؟", language="ar")
        assert resp.status_code == 200

        numbers = _extract_numbers(resp.json()["reply"])
        assert any(abs(n - actual_net) < 1.0 for n in numbers), (
            f"Expected net profit ~{actual_net} in reply. Numbers found: {numbers}"
        )

    def test_arabic_net_income_question(self, base_url, deterministic_accounting_bootstrap):
        """'كم صافي الدخل؟' should return actual net profit."""
        bs = deterministic_accounting_bootstrap
        _seed_pl_data(base_url, bs.auth_headers, bs)
        actual_net = float(_get_pl_net_profit(base_url, bs.auth_headers, bs.company_id)["net_profit"])

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "كم صافي الدخل؟", language="ar")
        assert resp.status_code == 200

        numbers = _extract_numbers(resp.json()["reply"])
        assert any(abs(n - actual_net) < 1.0 for n in numbers), (
            f"Expected net profit ~{actual_net} in reply. Numbers found: {numbers}"
        )

    def test_english_net_profit_question(self, base_url, deterministic_accounting_bootstrap):
        """'what is net profit?' should return actual net profit."""
        bs = deterministic_accounting_bootstrap
        _seed_pl_data(base_url, bs.auth_headers, bs)
        actual_net = float(_get_pl_net_profit(base_url, bs.auth_headers, bs.company_id)["net_profit"])

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "what is net profit?", language="en")
        assert resp.status_code == 200

        numbers = _extract_numbers(resp.json()["reply"])
        assert any(abs(n - actual_net) < 1.0 for n in numbers), (
            f"Expected net profit ~{actual_net} in reply. Numbers found: {numbers}"
        )

    def test_reply_does_not_show_zero_when_data_exists(self, base_url, deterministic_accounting_bootstrap):
        """If P&L has non-zero net profit, reply must not say 0.00."""
        bs = deterministic_accounting_bootstrap
        _seed_pl_data(base_url, bs.auth_headers, bs)
        actual_net = float(_get_pl_net_profit(base_url, bs.auth_headers, bs.company_id)["net_profit"])

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "كم الأرباح؟", language="ar")
        assert resp.status_code == 200

        reply = resp.json()["reply"]
        assert "Net Profit/Loss for all available data is 0.00" not in reply, (
            f"Reply incorrectly shows 0.00 when actual net profit is {actual_net}"
        )

    def test_report_question_intent_detected(self, base_url, deterministic_accounting_bootstrap):
        """Profit questions should be classified as report_question intent."""
        bs = deterministic_accounting_bootstrap

        for msg in ["كم الأرباح؟", "كم صافي الربح؟", "what is net profit?"]:
            resp = _gemini_request(
                base_url, bs.auth_headers, bs.company_id, msg,
                language="ar" if "كم" in msg else "en",
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["intent"] == "answer_report_question", (
                f"Message '{msg}' should produce intent 'answer_report_question', "
                f"got '{data['intent']}'"
            )

    def test_reply_includes_revenue_and_expenses(self, base_url, deterministic_accounting_bootstrap):
        """Reply should include at least the net profit in the answer."""
        bs = deterministic_accounting_bootstrap
        _seed_pl_data(base_url, bs.auth_headers, bs)
        pl = _get_pl_net_profit(base_url, bs.auth_headers, bs.company_id)
        actual_net = float(pl["net_profit"])
        actual_income = float(pl["total_income"])
        actual_expenses = float(pl["total_expenses"])

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "كم الأرباح إجمالاً؟", language="ar")
        assert resp.status_code == 200

        reply = resp.json()["reply"]
        numbers = _extract_numbers(reply)
        assert any(abs(n - actual_net) < 1.0 for n in numbers), (
            f"Expected net profit ~{actual_net} in reply. "
            f"Numbers: {numbers}. Reply: {reply[:300]}"
        )
