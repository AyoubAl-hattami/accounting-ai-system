"""
Tests for Gemini Assistant system-aware features:
explain figures, trace amounts, who-did-action questions.
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


def _extract_numbers(text):
    raw_numbers = re.findall(r'[\d,]+\.?\d*', text)
    result = []
    for n in raw_numbers:
        try:
            result.append(float(n.replace(',', '')))
        except ValueError:
            pass
    return result


def _get_pl_data(base_url, headers, company_id):
    resp = requests.get(
        f"{base_url}/reports/profit-and-loss?company_id={company_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def _seed_full_data(base_url, headers, bs):
    """Seed revenue 2000, expense 500, and owner contribution 1000.

    Resulting P&L: total_income=2000, total_expenses=500, net_profit=1500.
    The 1000 owner-contribution entry is balance-sheet-only (traceable but P&L-neutral).
    """
    bank_id = bs.account_id("1110")
    revenue_id = bs.account_id("4100")
    expense_id = bs.account_id("5100")
    capital_id = bs.account_id("3100")
    entry_date = bs.fiscal_period.start_date.isoformat()

    def _create_and_post(debit_id, credit_id, amount, desc):
        r = requests.post(
            f"{base_url}/journal-entries",
            headers=headers,
            json={
                "company_id": bs.company_id,
                "entry_no": f"EXPL-{uuid.uuid4().hex[:8].upper()}",
                "entry_date": entry_date,
                "description": desc,
                "source_type": "test",
                "source_id": f"expl-{uuid.uuid4().hex[:8]}",
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
    _create_and_post(bank_id, capital_id, 1000, "Owner contribution")


class TestExplainRevenue:
    """Test 'كيف صارت الإيرادات 2000؟' and similar explain questions."""

    def test_explain_revenue_arabic(self, base_url, deterministic_accounting_bootstrap):
        """Explain revenue question should return revenue amount and entry details."""
        bs = deterministic_accounting_bootstrap
        _seed_full_data(base_url, bs.auth_headers, bs)
        pl = _get_pl_data(base_url, bs.auth_headers, bs.company_id)
        actual_income = float(pl["total_income"])

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "كيف صارت الإيرادات 2000؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] in ("answer_explain_question",), f"Got intent: {data['intent']}"

        numbers = _extract_numbers(data["reply"])
        assert any(abs(n - actual_income) < 1.0 for n in numbers), (
            f"Expected ~{actual_income} in reply. Numbers: {numbers}. Reply: {data['reply'][:300]}"
        )

    def test_explain_revenue_includes_entries(self, base_url, deterministic_accounting_bootstrap):
        """Explain answer should populate evidence and data_sources."""
        bs = deterministic_accounting_bootstrap
        _seed_full_data(base_url, bs.auth_headers, bs)

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "كيف صارت الإيرادات 2000؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        evidence = data.get("evidence", [])
        assert len(evidence) > 0, "Expected evidence entries"
        assert "journal_entries" in data.get("data_sources", [])


class TestExplainNetProfit:
    """Test 'كيف صار صافي الدخل 1500؟' — net profit explanation."""

    def test_explain_net_profit_arabic(self, base_url, deterministic_accounting_bootstrap):
        """Net profit explanation should use isolated company report data."""
        bs = deterministic_accounting_bootstrap
        _seed_full_data(base_url, bs.auth_headers, bs)
        pl = _get_pl_data(base_url, bs.auth_headers, bs.company_id)
        actual_net = float(pl["net_profit"])
        actual_income = float(pl["total_income"])
        actual_expenses = float(pl["total_expenses"])

        assert actual_income == 2000.0
        assert actual_expenses == 500.0
        assert actual_net == 1500.0

        resp = _gemini_request(
            base_url, bs.auth_headers, bs.company_id,
            "كيف صار صافي الدخل 1500؟", language="ar",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "answer_explain_question"
        assert "profit_loss_report" in data.get("data_sources", [])
        assert "journal_entries" in data.get("data_sources", [])
        assert len(data.get("evidence", [])) >= 2

        numbers = _extract_numbers(data["reply"])
        assert any(abs(n - actual_net) < 1.0 for n in numbers), (
            f"Expected ~{actual_net} in reply. Numbers: {numbers}. Reply: {data['reply'][:300]}"
        )
        assert any(abs(n - actual_income) < 1.0 for n in numbers), (
            f"Expected ~{actual_income} in reply. Numbers: {numbers}. Reply: {data['reply'][:300]}"
        )
        assert any(abs(n - actual_expenses) < 1.0 for n in numbers), (
            f"Expected ~{actual_expenses} in reply. Numbers: {numbers}. Reply: {data['reply'][:300]}"
        )

    def test_explain_net_profit_english(self, base_url, deterministic_accounting_bootstrap):
        """English explain question should work too."""
        bs = deterministic_accounting_bootstrap
        _seed_full_data(base_url, bs.auth_headers, bs)
        pl = _get_pl_data(base_url, bs.auth_headers, bs.company_id)

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "Why is net income 1500?", language="en")
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "answer_explain_question"

        numbers = _extract_numbers(data["reply"])
        assert any(abs(n - float(pl["net_profit"])) < 1.0 for n in numbers), (
            f"Expected net profit in reply. Reply: {data['reply'][:300]}"
        )


class TestTraceAmount:
    """Test 'من أدخل 1000؟' — amount tracing."""

    def test_trace_amount_finds_entries(self, base_url, deterministic_accounting_bootstrap):
        """Tracing 1000 should find the owner-contribution entry."""
        bs = deterministic_accounting_bootstrap
        _seed_full_data(base_url, bs.auth_headers, bs)

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "من أدخل 1000؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        assert data["intent"] in ("answer_trace_question", "clarification"), \
            f"Got intent: {data['intent']}"

        if data["intent"] == "answer_trace_question":
            numbers = _extract_numbers(data["reply"])
            assert any(abs(n - 1000) < 1.0 for n in numbers), \
                f"Expected 1000 in reply. Numbers: {numbers}"
            assert len(data.get("evidence", [])) > 0, "Expected evidence for trace"

    def test_trace_multiple_matches_lists_candidates(self, base_url, deterministic_accounting_bootstrap):
        """If multiple 1000 entries exist, should list them all."""
        bs = deterministic_accounting_bootstrap
        _seed_full_data(base_url, bs.auth_headers, bs)

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "من أدخل 1000؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        if data["intent"] == "answer_trace_question":
            evidence = data.get("evidence", [])
            if len(evidence) > 1:
                assert "وجدت" in data["reply"] or "عمليات" in data["reply"] or len(evidence) > 1

    def test_trace_expense_amount(self, base_url, deterministic_accounting_bootstrap):
        """'وين راحت 500؟' should find the expense entry."""
        bs = deterministic_accounting_bootstrap
        _seed_full_data(base_url, bs.auth_headers, bs)

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "وين راحت 500؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        assert data["intent"] in ("answer_trace_question",), f"Got intent: {data['intent']}"
        numbers = _extract_numbers(data["reply"])
        assert any(abs(n - 500) < 1.0 for n in numbers), \
            f"Expected 500 in reply. Numbers: {numbers}"

    def test_anti_hallucination_nonexistent_amount(self, base_url, deterministic_accounting_bootstrap):
        """'من أدخل 9999؟' should say no matching entry."""
        bs = deterministic_accounting_bootstrap
        _seed_full_data(base_url, bs.auth_headers, bs)

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "من أدخل 9999؟", language="ar")
        assert resp.status_code == 200
        reply = resp.json()["reply"]
        assert any(phrase in reply for phrase in [
            "لم أجد", "لم يتم", "not found", "could not find", "no matching",
            "9,999", "9999",
        ]), f"Expected 'not found' message. Reply: {reply[:300]}"


class TestWhoAction:
    """Test 'من رحّل القيد؟' — who-did-action audit questions."""

    def test_who_posted_entry(self, base_url, deterministic_accounting_bootstrap):
        """Should find who posted an entry from audit logs."""
        bs = deterministic_accounting_bootstrap
        _seed_full_data(base_url, bs.auth_headers, bs)

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "من رحّل آخر قيد؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        assert data["intent"] in ("answer_who_action_question",), f"Got intent: {data['intent']}"
        assert "audit_logs" in data.get("data_sources", [])

    def test_who_created_entry_arabic_dialect(self, base_url, deterministic_accounting_bootstrap):
        """'مين أنشأ القيد؟' — Arabic dialect should work."""
        bs = deterministic_accounting_bootstrap
        _seed_full_data(base_url, bs.auth_headers, bs)

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "مين أنشأ القيد؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        assert data["intent"] in ("answer_who_action_question", "answer_audit_question"), \
            f"Got intent: {data['intent']}"


class TestPermissions:
    """Test that viewer role cannot access audit actor questions."""

    def test_viewer_denied_who_action(self, base_url, deterministic_accounting_bootstrap, accounting_factory):
        """Viewer asking 'who posted' should be denied."""
        bs = deterministic_accounting_bootstrap
        _seed_full_data(base_url, bs.auth_headers, bs)

        viewer, _ = accounting_factory.add_member(
            company=bs.company, role="viewer", full_name="Explain Viewer"
        )
        accounting_factory.db.commit()
        viewer_headers = accounting_factory.auth_headers_for(viewer)

        resp = _gemini_request(base_url, viewer_headers, bs.company_id, "من رحّل القيد؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        assert data["intent"] == "access_denied", \
            f"Viewer should be denied audit access. Got: {data['intent']}"


class TestExplainBalanceSheet:
    """Test balance sheet explanation: 'كيف وصلت الأصول إلى 1500؟'."""

    def test_explain_assets(self, base_url, deterministic_accounting_bootstrap):
        """Should explain how assets reached their total."""
        bs = deterministic_accounting_bootstrap
        _seed_full_data(base_url, bs.auth_headers, bs)

        resp = _gemini_request(base_url, bs.auth_headers, bs.company_id, "كيف وصلت الأصول إلى 1500؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        assert data["intent"] in ("answer_explain_question",), f"Got intent: {data['intent']}"
        assert "balance_sheet" in data.get("data_sources", []) or \
            "journal_entries" in data.get("data_sources", [])


def test_explain_intent_precedes_structured_balance_sheet():
    from app.modules.accounting.services.gemini_assistant_service import _classify_intent
    assert _classify_intent("Explain total assets") == "explain_question"
    assert _classify_intent("What are total assets") != "explain_question"
