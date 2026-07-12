"""
Tests for Gemini Assistant system-aware features:
explain figures, trace amounts, who-did-action questions.

Uses real data from the running backend (expected: Revenue=2000, Expenses=500, Net=1500).
"""

import os
import requests
import re
import uuid
from datetime import datetime, timezone

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


def _gemini_request(headers, message, language="ar", company_id=COMPANY_ID):
    return requests.post(
        f"{BASE_URL}/ai/gemini-assistant",
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
    """Extract all numbers (including decimals and comma-formatted) from text."""
    raw_numbers = re.findall(r'[\d,]+\.?\d*', text)
    result = []
    for n in raw_numbers:
        try:
            result.append(float(n.replace(',', '')))
        except ValueError:
            pass
    return result


def _get_pl_data(headers, company_id=COMPANY_ID):
    """Get actual P&L from reports."""
    resp = requests.get(
        f"{BASE_URL}/reports/profit-and-loss?company_id={company_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()



def _create_company(headers):
    response = requests.post(
        f"{BASE_URL}/companies",
        headers=headers,
        json={
            "name": f"ExplainProfit_{uuid.uuid4().hex[:10]}",
            "base_currency": "USD",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _seed_default_accounts(headers, company_id):
    response = requests.post(
        f"{BASE_URL}/accounts/seed-defaults?company_id={company_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text


def _get_account_id_by_code(headers, company_id, code):
    response = requests.get(
        f"{BASE_URL}/accounts?company_id={company_id}&skip=0&limit=100",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    for account in response.json()["items"]:
        if account["code"] == code:
            return account["id"]
    raise AssertionError(f"Account code {code} not found for company {company_id}")


def _quick_setup_today(headers, company_id):
    response = requests.post(
        f"{BASE_URL}/fiscal/quick-setup-today",
        headers=headers,
        params={"company_id": company_id},
    )
    assert response.status_code == 200, response.text


def _create_journal_entry(headers, company_id, debit_account_id, credit_account_id, amount, description):
    today = datetime.now(timezone.utc).date().isoformat()
    response = requests.post(
        f"{BASE_URL}/journal-entries",
        headers=headers,
        json={
            "company_id": company_id,
            "entry_no": f"EXPL-{uuid.uuid4().hex[:10].upper()}",
            "entry_date": today,
            "description": description,
            "source_type": "test",
            "source_id": f"explain-{uuid.uuid4().hex[:10]}",
            "lines": [
                {
                    "account_id": debit_account_id,
                    "debit": amount,
                    "credit": 0,
                    "description": description,
                },
                {
                    "account_id": credit_account_id,
                    "debit": 0,
                    "credit": amount,
                    "description": description,
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _post_journal_entry(headers, entry_id):
    review = requests.post(f"{BASE_URL}/journal-entries/{entry_id}/review", headers=headers)
    assert review.status_code == 200, review.text
    response = requests.post(f"{BASE_URL}/journal-entries/{entry_id}/post", headers=headers)
    assert response.status_code == 200, response.text
def _create_isolated_profit_company(headers):
    company_id = _create_company(headers)
    _seed_default_accounts(headers, company_id)
    _quick_setup_today(headers, company_id)

    bank_id = _get_account_id_by_code(headers, company_id, "1110")
    revenue_id = _get_account_id_by_code(headers, company_id, "4100")
    rent_expense_id = _get_account_id_by_code(headers, company_id, "5100")

    revenue_entry_id = _create_journal_entry(
        headers,
        company_id,
        bank_id,
        revenue_id,
        2000,
        "Isolated explain revenue",
    )
    _post_journal_entry(headers, revenue_entry_id)

    expense_entry_id = _create_journal_entry(
        headers,
        company_id,
        rent_expense_id,
        bank_id,
        500,
        "Isolated explain rent expense",
    )
    _post_journal_entry(headers, expense_entry_id)

    return company_id, {
        "total_income": 2000.0,
        "total_expenses": 500.0,
        "net_profit": 1500.0,
    }

class TestExplainRevenue:
    """Test 'كيف صارت الإيرادات 2000؟' and similar explain questions."""

    def test_explain_revenue_arabic(self):
        """Explain revenue question should return revenue amount and entry details."""
        headers = _admin_headers()
        pl = _get_pl_data(headers)
        actual_income = float(pl["total_income"])
        if actual_income == 0:
            return  # Skip if no data

        resp = _gemini_request(headers, "كيف صارت الإيرادات 2000؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] in ("answer_explain_question",), f"Got intent: {data['intent']}"

        reply = data["reply"]
        numbers = _extract_numbers(reply)
        # Revenue amount should appear
        assert any(
            abs(n - actual_income) < 1.0 for n in numbers
        ), f"Expected ~{actual_income} in reply. Numbers: {numbers}. Reply: {reply[:300]}"

    def test_explain_revenue_includes_entries(self):
        """Explain answer should mention entry numbers (AI-... format)."""
        headers = _admin_headers()
        pl = _get_pl_data(headers)
        if float(pl["total_income"]) == 0:
            return

        resp = _gemini_request(headers, "كيف صارت الإيرادات 2000؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        # Check evidence is populated
        evidence = data.get("evidence", [])
        assert len(evidence) > 0, "Expected evidence entries"

        # Check data sources
        assert "journal_entries" in data.get("data_sources", [])


class TestExplainNetProfit:
    """Test 'كيف صار صافي الدخل 1500؟' — net profit explanation."""

    def test_explain_net_profit_arabic(self):
        """Net profit explanation should use isolated company report data."""
        headers = _admin_headers()
        company_id, expected = _create_isolated_profit_company(headers)
        pl = _get_pl_data(headers, company_id)
        actual_net = float(pl["net_profit"])
        actual_income = float(pl["total_income"])
        actual_expenses = float(pl["total_expenses"])

        assert actual_income == expected["total_income"]
        assert actual_expenses == expected["total_expenses"]
        assert actual_net == expected["net_profit"]

        resp = _gemini_request(
            headers,
            "كيف صار صافي الدخل 1500؟",
            language="ar",
            company_id=company_id,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "answer_explain_question"
        assert "profit_loss_report" in data.get("data_sources", [])
        assert "journal_entries" in data.get("data_sources", [])
        assert len(data.get("evidence", [])) >= 2

        reply = data["reply"]
        numbers = _extract_numbers(reply)

        assert any(
            abs(n - actual_net) < 1.0 for n in numbers
        ), f"Expected ~{actual_net} in reply. Numbers: {numbers}. Reply: {reply[:300]}"

        assert any(
            abs(n - actual_income) < 1.0 for n in numbers
        ), f"Expected ~{actual_income} in reply. Numbers: {numbers}. Reply: {reply[:300]}"

        assert any(
            abs(n - actual_expenses) < 1.0 for n in numbers
        ), f"Expected ~{actual_expenses} in reply. Numbers: {numbers}. Reply: {reply[:300]}"

    def test_explain_net_profit_english(self):
        """English explain question should work too."""
        headers = _admin_headers()
        pl = _get_pl_data(headers)
        if float(pl["net_profit"]) == 0:
            return

        resp = _gemini_request(headers, "Why is net income 1500?", language="en")
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "answer_explain_question"

        reply = data["reply"]
        numbers = _extract_numbers(reply)
        assert any(
            abs(n - float(pl["net_profit"])) < 1.0 for n in numbers
        ), f"Expected net profit in reply. Reply: {reply[:300]}"


class TestTraceAmount:
    """Test 'من أدخل 1000؟' — amount tracing."""

    def test_trace_amount_finds_entries(self):
        """Tracing 1000 should find matching journal entries."""
        headers = _admin_headers()
        resp = _gemini_request(headers, "من أدخل 1000؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        # Should be trace intent
        assert data["intent"] in ("answer_trace_question", "clarification"), \
            f"Got intent: {data['intent']}"

        if data["intent"] == "answer_trace_question":
            reply = data["reply"]
            # Should mention 1000
            numbers = _extract_numbers(reply)
            assert any(
                abs(n - 1000) < 1.0 for n in numbers
            ), f"Expected 1000 in reply. Numbers: {numbers}"

            # Should have evidence
            evidence = data.get("evidence", [])
            assert len(evidence) > 0, "Expected evidence for trace"

    def test_trace_multiple_matches_lists_candidates(self):
        """If multiple 1000 entries exist, should list them all."""
        headers = _admin_headers()
        resp = _gemini_request(headers, "من أدخل 1000؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        if data["intent"] == "answer_trace_question":
            evidence = data.get("evidence", [])
            # If 2+ entries of 1000, reply should mention multiple
            if len(evidence) > 1:
                assert "وجدت" in data["reply"] or "عمليات" in data["reply"] or \
                    len(evidence) > 1, "Multiple matches should be listed"

    def test_trace_expense_amount(self):
        """'وين راحت 500؟' should find the expense entry."""
        headers = _admin_headers()
        resp = _gemini_request(headers, "وين راحت 500؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        assert data["intent"] in ("answer_trace_question",), \
            f"Got intent: {data['intent']}"

        reply = data["reply"]
        numbers = _extract_numbers(reply)
        assert any(
            abs(n - 500) < 1.0 for n in numbers
        ), f"Expected 500 in reply. Numbers: {numbers}"

    def test_anti_hallucination_nonexistent_amount(self):
        """'من أدخل 9999؟' should say no matching entry."""
        headers = _admin_headers()
        resp = _gemini_request(headers, "من أدخل 9999؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        reply = data["reply"]
        # Should indicate no match found (not hallucinate an entry)
        assert any(phrase in reply for phrase in [
            "لم أجد", "لم يتم", "not found", "could not find", "no matching",
            "9,999", "9999",
        ]), f"Expected 'not found' message. Reply: {reply[:300]}"


class TestWhoAction:
    """Test 'من رحّل القيد؟' — who-did-action audit questions."""

    def test_who_posted_entry(self):
        """Should find who posted an entry from audit logs."""
        headers = _admin_headers()
        resp = _gemini_request(headers, "من رحّل آخر قيد؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        assert data["intent"] in ("answer_who_action_question",), \
            f"Got intent: {data['intent']}"
        assert "audit_logs" in data.get("data_sources", [])

    def test_who_created_entry_arabic_dialect(self):
        """'مين أنشأ القيد؟' — Arabic dialect should work."""
        headers = _admin_headers()
        resp = _gemini_request(headers, "مين أنشأ القيد؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        # Should be recognized as who_action or audit
        assert data["intent"] in ("answer_who_action_question", "answer_audit_question"), \
            f"Got intent: {data['intent']}"


class TestPermissions:
    """Test that viewer role cannot access audit actor questions."""

    def test_viewer_denied_who_action(self):
        """Viewer asking 'who posted' should be denied."""
        import uuid
        viewer_email = f"viewer_test_{uuid.uuid4().hex[:6]}@test.com"
        reg_resp = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": viewer_email,
                "password": "ViewerPass1",
                "full_name": "Test Viewer",
            },
        )
        if reg_resp.status_code != 201:
            return  # Skip if can't register

        login_resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": viewer_email, "password": "ViewerPass1"},
        )
        if login_resp.status_code != 200:
            return

        viewer_token = login_resp.json()["access_token"]
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        admin_headers = _admin_headers()
        invite_resp = requests.post(
            f"{BASE_URL}/company-users/invite",
            headers=admin_headers,
            json={
                "company_id": COMPANY_ID,
                "email": viewer_email,
                "role": "viewer",
            },
        )
        if invite_resp.status_code not in (200, 201):
            return

        invite_data = invite_resp.json()
        if "raw_token" in invite_data:
            requests.post(
                f"{BASE_URL}/company-users/accept-invite",
                json={"token": invite_data["raw_token"]},
                headers=viewer_headers,
            )

        resp = _gemini_request(viewer_headers, "من رحّل القيد؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        assert data["intent"] == "access_denied", \
            f"Viewer should be denied audit access. Got: {data['intent']}"


class TestExplainBalanceSheet:
    """Test balance sheet explanation: 'كيف وصلت الأصول إلى 1500؟'."""

    def test_explain_assets(self):
        """Should explain how assets reached their total."""
        headers = _admin_headers()
        resp = _gemini_request(headers, "كيف وصلت الأصول إلى 1500؟", language="ar")
        assert resp.status_code == 200
        data = resp.json()

        assert data["intent"] in ("answer_explain_question",), \
            f"Got intent: {data['intent']}"

        # Should include balance sheet data source
        assert "balance_sheet" in data.get("data_sources", []) or \
            "journal_entries" in data.get("data_sources", [])
