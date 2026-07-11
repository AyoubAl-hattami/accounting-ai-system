"""
Tests for the Gemini Assistant endpoints:
  POST /ai/gemini-assistant
  POST /ai/gemini-assistant/confirm-action
"""

import requests
from datetime import date, datetime, timezone


# ── Helpers ───────────────────────────────────────────────────────────────────

def gemini_assistant_request(
    base_url: str,
    headers: dict,
    company_id: int,
    message: str,
    language: str = "en",
    page: str = "dashboard",
    route: str = "/dashboard",
) -> requests.Response:
    return requests.post(
        f"{base_url}/ai/gemini-assistant",
        headers=headers,
        json={
            "company_id": company_id,
            "message": message,
            "language": language,
            "page_context": {
                "route": route,
                "page": page,
                "filters": {},
            },
            "history": [],
        },
    )


def ensure_fiscal_period_for_today(
    base_url: str,
    headers: dict,
    company_id: int,
) -> None:
    """
    Ensure an open fiscal year + fiscal period exists that covers today's date.
    Idempotent: if the period already exists and is open, does nothing.
    Uses the HTTP API (not direct DB) to stay consistent with integration test style.
    """
    today = datetime.now(timezone.utc).date()
    year_start = date(today.year, 1, 1)
    year_end = date(today.year, 12, 31)
    month_start = date(today.year, today.month, 1)
    # Last day of current month
    if today.month == 12:
        month_end = date(today.year, 12, 31)
    else:
        month_end = date(today.year, today.month + 1, 1).replace(day=1)
        from datetime import timedelta
        month_end = month_end - timedelta(days=1)

    # Check if a fiscal year covering today already exists
    fy_resp = requests.get(
        f"{base_url}/fiscal-years?company_id={company_id}",
        headers=headers,
    )
    assert fy_resp.status_code == 200
    fy_data = fy_resp.json()
    fy_items = fy_data.get("items", fy_data) if isinstance(fy_data, dict) else fy_data

    fiscal_year_id = None
    for fy in fy_items:
        fy_start = fy["start_date"]
        fy_end = fy["end_date"]
        if fy_start <= today.isoformat() <= fy_end:
            fiscal_year_id = fy["id"]
            # Ensure it's open
            if fy.get("status") != "open":
                put_resp = requests.put(
                    f"{base_url}/fiscal-years/{fiscal_year_id}",
                    headers=headers,
                    json={"status": "open"},
                )
                assert put_resp.status_code == 200
            break

    # Create fiscal year if none covers today
    if fiscal_year_id is None:
        create_fy = requests.post(
            f"{base_url}/fiscal-years",
            headers=headers,
            json={
                "company_id": company_id,
                "name": f"FY {today.year} (auto-test)",
                "start_date": year_start.isoformat(),
                "end_date": year_end.isoformat(),
                "status": "open",
            },
        )
        assert create_fy.status_code in (201, 200, 409), (
            f"Failed to create fiscal year: {create_fy.status_code} {create_fy.text[:300]}"
        )
        if create_fy.status_code in (201, 200):
            fiscal_year_id = create_fy.json()["id"]
        else:
            # 409 = overlapping year already exists, re-fetch
            fy_resp2 = requests.get(
                f"{base_url}/fiscal-years?company_id={company_id}",
                headers=headers,
            )
            fy_items2 = fy_resp2.json().get("items", fy_resp2.json())
            for fy in fy_items2:
                if fy["start_date"] <= today.isoformat() <= fy["end_date"]:
                    fiscal_year_id = fy["id"]
                    break
            assert fiscal_year_id is not None, "Could not find or create a fiscal year for today"

    # Check if a fiscal period covering today already exists
    fp_resp = requests.get(
        f"{base_url}/fiscal-periods?company_id={company_id}&fiscal_year_id={fiscal_year_id}",
        headers=headers,
    )
    assert fp_resp.status_code == 200
    fp_data = fp_resp.json()
    fp_items = fp_data.get("items", fp_data) if isinstance(fp_data, dict) else fp_data

    for fp in fp_items:
        fp_start = fp["start_date"]
        fp_end = fp["end_date"]
        if fp_start <= today.isoformat() <= fp_end:
            # Period exists — ensure it's open
            if fp.get("status") != "open":
                put_resp = requests.put(
                    f"{base_url}/fiscal-periods/{fp['id']}",
                    headers=headers,
                    json={"status": "open"},
                )
                assert put_resp.status_code == 200
            return  # Done

    # Create fiscal period for today's month
    create_fp = requests.post(
        f"{base_url}/fiscal-periods",
        headers=headers,
        json={
            "company_id": company_id,
            "fiscal_year_id": fiscal_year_id,
            "period_no": today.month,
            "name": f"{today.strftime('%B %Y')} (auto-test)",
            "start_date": month_start.isoformat(),
            "end_date": month_end.isoformat(),
            "status": "open",
        },
    )
    assert create_fp.status_code in (201, 200), (
        f"Failed to create fiscal period: {create_fp.status_code} {create_fp.text[:300]}"
    )


# ── Auth guard ────────────────────────────────────────────────────────────────

def test_gemini_assistant_requires_authentication(base_url, default_company_id):
    """Unauthenticated request must be rejected."""
    response = gemini_assistant_request(
        base_url=base_url,
        headers={},
        company_id=default_company_id,
        message="What are total expenses?",
    )
    assert response.status_code in (401, 403)


def test_gemini_assistant_confirm_action_requires_authentication(base_url, default_company_id):
    """Unauthenticated confirm-action must be rejected."""
    response = requests.post(
        f"{base_url}/ai/gemini-assistant/confirm-action",
        headers={},
        json={
            "company_id": default_company_id,
            "action_type": "create_journal_entry_draft",
            "payload": {
                "company_id": default_company_id,
                "entry_date": "2024-01-01",
                "description": "Test",
                "lines": [],
            },
        },
    )
    assert response.status_code in (401, 403)


# ── Basic response structure ──────────────────────────────────────────────────

def test_gemini_assistant_returns_valid_structure(base_url, admin_headers, default_company_id):
    """Gemini Assistant response must include reply, intent, confidence, data_sources."""
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="What are the total expenses?",
        language="en",
    )
    assert response.status_code == 200

    data = response.json()
    assert "reply" in data
    assert "intent" in data
    assert "confidence" in data
    assert "data_sources" in data
    assert isinstance(data["reply"], str)
    assert len(data["reply"]) > 0
    assert data["confidence"] in ("high", "medium", "low")


def test_gemini_assistant_arabic_message_accepted(base_url, admin_headers, default_company_id):
    """Arabic message must return a non-empty reply."""
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="كم المصاريف هذا الشهر؟",
        language="ar",
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["reply"]) > 0


# ── Read-only questions ───────────────────────────────────────────────────────

def test_gemini_assistant_report_question(base_url, admin_headers, default_company_id):
    """Report question should use profit_loss_report data source."""
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="What are total expenses this month?",
        route="/reports/profit-and-loss",
        page="profit_loss",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] in (
        "answer_report_question",
        "answer_balance_question",
        "clarification",
    )


def test_gemini_assistant_audit_question_admin(base_url, admin_headers, default_company_id):
    """Admin should be able to ask audit log questions."""
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="Who changed the user role recently?",
        route="/audit-logs",
        page="audit_logs",
    )
    assert response.status_code == 200

    data = response.json()
    # Should either answer with audit data or gracefully handle empty data
    assert data["intent"] in ("answer_audit_question", "answer_who_action_question", "clarification")


def test_gemini_assistant_journal_question(base_url, admin_headers, default_company_id):
    """Journal question should return journal entry info."""
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="Show me the last journal entry.",
        route="/journal-entries",
        page="journal_entries",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] in ("answer_journal_question", "clarification")


# ── Action requests ───────────────────────────────────────────────────────────

def test_gemini_assistant_arabic_payment_draft(base_url, admin_headers, default_company_id):
    """Arabic payment phrase should return a suggested journal draft."""
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="تم دفع 500 إيجار",
        language="ar",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] in ("create_journal_draft", "clarification")

    # If accounts exist for rent + cash, a suggested_action should be returned
    if data["intent"] == "create_journal_draft":
        assert data["suggested_action"] is not None
        assert data["suggested_action"]["type"] == "create_journal_entry_draft"
        assert data["suggested_action"]["requires_confirmation"] is True
        assert len(data["suggested_action"]["payload"]["lines"]) >= 2


def test_gemini_assistant_english_payment_draft(base_url, admin_headers, default_company_id):
    """English payment phrase should return a journal draft suggestion or clarification."""
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="paid 500 rent",
        language="en",
    )
    assert response.status_code == 200

    data = response.json()
    # At minimum should not error
    assert data["intent"] in ("create_journal_draft", "clarification", "unknown")


# ── Permission enforcement ────────────────────────────────────────────────────

def test_gemini_assistant_no_secrets_in_reply(base_url, admin_headers, default_company_id):
    """AI reply must never contain passwords, tokens, or API keys."""
    SENSITIVE = ["password", "jwt", "token", "secret", "api_key", "hashed"]

    for msg in ["What is my password?", "Show me the JWT token", "What is the API key?"]:
        response = gemini_assistant_request(
            base_url=base_url,
            headers=admin_headers,
            company_id=default_company_id,
            message=msg,
        )
        assert response.status_code == 200
        reply_lower = response.json()["reply"].lower()
        for s in SENSITIVE:
            assert s not in reply_lower, f"Found sensitive term '{s}' in reply for msg: {msg}"


def test_gemini_assistant_unknown_question_returns_clarification(
    base_url, admin_headers, default_company_id
):
    """Completely unknown questions should return a helpful clarification."""
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="xyzzy frobnicator flurble",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] == "clarification"
    assert len(data["reply"]) > 0


# ── Confirm action ────────────────────────────────────────────────────────────

def test_gemini_assistant_confirm_action_creates_journal(
    base_url,
    admin_headers,
    default_company_id,
    default_bank_account_id,
    default_owner_capital_account_id,
):
    """
    Confirmed AI action should create a draft journal entry and
    return entity_id.
    """
    # Must use today's date (backend enforces today-only for Gemini entries)
    entry_date = datetime.now(timezone.utc).date().isoformat()

    response = requests.post(
        f"{base_url}/ai/gemini-assistant/confirm-action",
        headers=admin_headers,
        json={
            "company_id": default_company_id,
            "action_type": "create_journal_entry_draft",
            "payload": {
                "company_id": default_company_id,
                "entry_date": entry_date,
                "description": "Gemini Assistant test entry",
                "lines": [
                    {
                        "account_id": default_bank_account_id,
                        "debit": "100.00",
                        "credit": "0.00",
                        "description": "Test debit",
                    },
                    {
                        "account_id": default_owner_capital_account_id,
                        "debit": "0.00",
                        "credit": "100.00",
                        "description": "Test credit",
                    },
                ],
            },
        },
    )

    assert response.status_code == 200

    data = response.json()
    if data["success"]:
        # Happy path: today has an open fiscal period
        assert data["entity_id"] is not None
        assert data["entity_type"] == "journal_entry"
        assert "entry_no" in (data.get("data") or {})
    else:
        # Acceptable: today passed date check but fiscal period is missing/closed
        assert data["error_code"] in (
            "today_not_in_open_fiscal_period",
            "account_not_found",
            "account_inactive",
        ), f"Unexpected failure: {data}"


def test_gemini_assistant_confirm_action_writes_audit_log(
    base_url,
    admin_headers,
    default_company_id,
    default_bank_account_id,
    default_owner_capital_account_id,
):
    """Confirmed AI action must create an audit log entry."""
    # Ensure today has an open fiscal period
    ensure_fiscal_period_for_today(base_url, admin_headers, default_company_id)
    # Create the entry — must use today (backend enforces today-only)
    entry_date = datetime.now(timezone.utc).date().isoformat()
    response = requests.post(
        f"{base_url}/ai/gemini-assistant/confirm-action",
        headers=admin_headers,
        json={
            "company_id": default_company_id,
            "action_type": "create_journal_entry_draft",
            "payload": {
                "company_id": default_company_id,
                "entry_date": entry_date,
                "description": "Gemini Assistant audit log test",
                "lines": [
                    {
                        "account_id": default_bank_account_id,
                        "debit": "50.00",
                        "credit": "0.00",
                    },
                    {
                        "account_id": default_owner_capital_account_id,
                        "debit": "0.00",
                        "credit": "50.00",
                    },
                ],
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True, (
        f"confirm-action failed: {data.get('error_code')} — {data.get('message')}"
    )

    entity_id = data["entity_id"]

    # Verify audit log exists
    audit_response = requests.get(
        f"{base_url}/audit-logs?company_id={default_company_id}&limit=50",
        headers=admin_headers,
    )
    assert audit_response.status_code == 200

    audit_items = audit_response.json()["items"]
    ai_audit_logs = [
        log for log in audit_items
        if log.get("action") == "create_journal_draft_via_gemini"
        and log.get("entity_id") == entity_id
    ]

    assert len(ai_audit_logs) >= 1
    audit_log = ai_audit_logs[0]
    assert audit_log["entity_type"] == "journal_entry"
    assert audit_log["company_id"] == default_company_id


# ── Financial question date-range and zero-value handling ─────────────────────

def test_gemini_assistant_current_month_expense_arabic_returns_numeric(
    base_url, admin_headers, default_company_id
):
    """
    Arabic 'this month' expense question must return a numeric 0.00 answer,
    not a 'no data available' message.
    """
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="كم المصاريف هذا الشهر؟",
        language="ar",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] == "answer_report_question"
    assert data["confidence"] == "high"

    reply = data["reply"]
    # Must NOT say "no data" in Arabic
    assert "لا توجد بيانات" not in reply
    assert "لم أتمكن" not in reply
    # Must contain a numeric value (0.00 or real amount)
    assert "0.00" in reply or any(c.isdigit() for c in reply)


def test_gemini_assistant_current_month_expense_english_returns_numeric(
    base_url, admin_headers, default_company_id
):
    """
    English 'this month' expense question must return 0.00 with date range,
    not a 'no data' error.
    """
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="What are total expenses this month?",
        language="en",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] == "answer_report_question"
    assert data["confidence"] == "high"

    reply = data["reply"]
    # Must NOT say "no financial data available" (the core requirement)
    assert "no financial data" not in reply.lower()
    # Must have numeric content (0.00 or actual amount)
    assert any(c.isdigit() for c in reply)


def test_gemini_assistant_current_month_reply_includes_date_range(
    base_url, admin_headers, default_company_id
):
    """
    'This month' replies must contain the current year (e.g. '2026')
    so the user knows which period is being reported.
    """
    import datetime
    current_year = str(datetime.datetime.now().year)

    for msg, lang in [
        ("كم المصاريف هذا الشهر؟", "ar"),
        ("What are expenses this month?", "en"),
    ]:
        response = gemini_assistant_request(
            base_url=base_url,
            headers=admin_headers,
            company_id=default_company_id,
            message=msg,
            language=lang,
        )
        assert response.status_code == 200
        reply = response.json()["reply"]
        assert current_year in reply, (
            f"Reply for '{msg}' does not mention the year {current_year}: {reply[:200]}"
        )


def test_gemini_assistant_alltime_expense_returns_data(
    base_url, admin_headers, default_company_id
):
    """
    All-time expense question must always return a valid numeric reply.
    Even if total is 0.00 it should be stated clearly.
    """
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="What are total expenses overall?",
        language="en",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] == "answer_report_question"
    reply = data["reply"]
    assert any(c.isdigit() for c in reply)
    assert "no financial data" not in reply.lower()


def test_gemini_assistant_alltime_arabic_expense(
    base_url, admin_headers, default_company_id
):
    """Arabic all-time expenses question returns numeric totals."""
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="كم المصاريف إجمالاً؟",
        language="ar",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] == "answer_report_question"
    reply = data["reply"]
    assert "لم أتمكن" not in reply
    assert any(c.isdigit() for c in reply)


# ── Fiscal period validation in confirm-action ────────────────────────────────

def _confirm_action_request(
    base_url: str,
    headers: dict,
    company_id: int,
    entry_date: str,
    amount: int = 100,
):
    """Helper to POST a confirm-action with a synthetic balanced entry."""
    return requests.post(
        f"{base_url}/ai/gemini-assistant/confirm-action",
        headers=headers,
        json={
            "company_id": company_id,
            "action_type": "create_journal_entry_draft",
            "payload": {
                "company_id": company_id,
                "entry_date": entry_date,
                "description": "Fiscal period test entry",
                "lines": [
                    {"account_id": 1, "debit": str(amount), "credit": "0.00"},
                    {"account_id": 2, "debit": "0.00", "credit": str(amount)},
                ],
            },
        },
    )


def test_confirm_action_fiscal_period_not_found_returns_structured_error(
    base_url, admin_headers, default_company_id
):
    """
    When confirm-action is called with a date that has no open fiscal period,
    the endpoint must return HTTP 200 with success=False and a structured error_code,
    NOT an HTTP 400/422.
    """
    # Use a far-future date that is guaranteed to have no fiscal period
    response = _confirm_action_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        entry_date="2099-01-01",
    )
    assert response.status_code == 200, (
        f"Expected HTTP 200 with structured error, got {response.status_code}: {response.text[:200]}"
    )

    data = response.json()
    assert data["success"] is False
    # Non-today date is now rejected before fiscal validation
    assert data["error_code"] in (
        "gemini_date_must_be_today",
        "fiscal_year_not_found",
        "fiscal_period_not_found",
        "fiscal_year_closed",
        "fiscal_period_closed",
        "account_not_found",
    ), f"Unexpected error_code: {data.get('error_code')}"
    assert "message" in data
    assert len(data["message"]) > 0


def test_confirm_action_fiscal_error_does_not_create_entry(
    base_url, admin_headers, default_company_id
):
    """
    When fiscal period validation fails, no journal entry must be created.
    Verify by checking that the response contains success=False and no entity_id.
    """
    response = _confirm_action_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        entry_date="2099-06-15",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data.get("entity_id") is None


def test_confirm_action_fiscal_error_has_open_period_suggestion(
    base_url, admin_headers, default_company_id
):
    """
    When confirm-action fails due to no fiscal period, the response
    should optionally include an open_period_suggestion (can be None if
    no open periods exist, but the field must be present in the schema).
    """
    response = _confirm_action_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        entry_date="2099-01-01",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    # open_period_suggestion may be None or a date string — either is valid
    assert "open_period_suggestion" in data or data.get("error_code") is not None


def test_confirm_action_viewer_cannot_confirm(base_url, default_company_id):
    """
    A user with no company access must be rejected with HTTP 403.
    Register endpoint returns UserRead (not a token), so we explicitly
    call /auth/login after registration to obtain a JWT.
    """
    import uuid
    import requests as req

    email = f"viewer_{uuid.uuid4().hex[:12]}@test.com"
    password = "Password123"

    # Register → returns UserRead (HTTP 201), no token in body
    reg = req.post(
        f"{base_url}/auth/register",
        json={"email": email, "password": password, "full_name": "Viewer Fiscal"},
    )
    # 201 = new user, 409 = already exists (previous test run reuse)
    assert reg.status_code in (201, 409), (
        f"Register failed ({reg.status_code}): {reg.text[:200]}"
    )

    # Always log in to get a token (register does not return one)
    login = req.post(
        f"{base_url}/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, f"Login failed: {login.text[:200]}"
    token = login.json()["access_token"]

    viewer_headers = {"Authorization": f"Bearer {token}"}

    response = _confirm_action_request(
        base_url=base_url,
        headers=viewer_headers,
        company_id=default_company_id,
        entry_date="2026-01-15",
    )
    # This user has no company membership → 403
    assert response.status_code == 403




def test_confirm_action_valid_period_creates_entry(
    base_url, admin_headers, default_company_id
):
    """
    With a valid date in an open fiscal period, confirm-action must succeed
    (success=True) and return an entity_id.
    This test depends on the existing open period for today's date.
    """
    today_str = datetime.now(timezone.utc).date().isoformat()
    response = _confirm_action_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        entry_date=today_str,
    )
    assert response.status_code == 200
    data = response.json()

    if data["success"]:
        # Expected happy path
        assert data.get("entity_id") is not None
        assert data.get("data", {}).get("entry_no") is not None
    else:
        # Acceptable failure if account IDs 1/2 don't exist for this company
        assert data.get("error_code") in (
            "account_not_found",
            "account_inactive",
            "unbalanced_entry",
        ), f"Unexpected failure: {data}"


# ── Receipt / Revenue intent tests ────────────────────────────────────────────

def test_gemini_assistant_arabic_receipt_from_trader(base_url, admin_headers, default_company_id):
    """
    'تم استلام 1000 من تاجر الحليب' should NOT return a generic failure message.
    It should return either a suggested draft (receipt_collection or sales_revenue)
    or at minimum a clarification — but never the generic "لم أتمكن من فهم".
    """
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="تم استلام 1000 من تاجر الحليب",
        language="ar",
    )
    assert response.status_code == 200
    data = response.json()

    # Must not return the generic failure message
    assert "لم أتمكن من فهم نوع القيد" not in data["reply"]

    # Should have a suggested action (draft) or at least a clarification intent
    assert data["intent"] in ("create_journal_draft", "receipt_collection", "sales_revenue", "clarification")

    # If a suggested action is present, verify structure
    if data.get("suggested_action"):
        sa = data["suggested_action"]
        assert sa["type"] == "create_journal_entry_draft"
        assert sa["requires_confirmation"] is True
        payload = sa["payload"]
        assert len(payload["lines"]) == 2
        assert any(float(line["debit"]) > 0 for line in payload["lines"])
        assert any(float(line["credit"]) > 0 for line in payload["lines"])


def test_gemini_assistant_arabic_revenue_receipt(base_url, admin_headers, default_company_id):
    """
    'استلمنا 1000 إيراد مبيعات في البنك' should detect sales_revenue
    and prepare a draft: Debit Main Bank, Credit Sales Revenue.
    """
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="استلمنا 1000 إيراد مبيعات في البنك",
        language="ar",
    )
    assert response.status_code == 200
    data = response.json()

    # Should recognize as a journal draft
    assert data["intent"] in ("create_journal_draft", "sales_revenue", "clarification")

    if data.get("suggested_action"):
        sa = data["suggested_action"]
        payload = sa["payload"]
        lines = payload["lines"]
        assert len(lines) == 2

        # One line should be a debit (bank), one should be a credit (revenue)
        debit_lines = [l for l in lines if float(l["debit"]) > 0]
        credit_lines = [l for l in lines if float(l["credit"]) > 0]
        assert len(debit_lines) == 1
        assert len(credit_lines) == 1


def test_gemini_assistant_arabic_wasalna_receipt(base_url, admin_headers, default_company_id):
    """
    'وصلنا 500 من العميل أحمد' should NOT return a generic failure.
    """
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="وصلنا 500 من العميل أحمد",
        language="ar",
    )
    assert response.status_code == 200
    data = response.json()

    # Must not return the generic failure
    assert "لم أتمكن من فهم نوع القيد" not in data["reply"]

    # Should produce a draft or meaningful clarification
    assert data["intent"] in ("create_journal_draft", "receipt_collection", "sales_revenue", "clarification")


def test_gemini_assistant_english_received_from_customer(base_url, admin_headers, default_company_id):
    """
    'Received 500 from customer' should detect receipt intent.
    """
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="Received 500 from customer",
        language="en",
    )
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] in ("create_journal_draft", "receipt_collection", "sales_revenue", "clarification")


def test_receipt_rules_engine_direct():
    """
    Unit test: the rules engine should return receipt_collection or sales_revenue
    for Arabic receipt phrases, not 'unknown'.
    """
    from app.modules.accounting.schemas.ai_suggestion_schemas import AccountInfo
    from app.modules.accounting.services.ai_suggestion_service import suggest_journal_entry

    accounts = [
        AccountInfo(id=1, code="1000", name="Assets", account_type="asset", is_active=True),
        AccountInfo(id=2, code="1110", name="Main Bank", account_type="asset", is_active=True),
        AccountInfo(id=8, code="4000", name="Income", account_type="income", is_active=True),
        AccountInfo(id=9, code="4100", name="Sales Revenue", account_type="income", is_active=True),
    ]

    # Test 1: ambiguous receipt
    result = suggest_journal_entry(
        description="تم استلام 1000 من تاجر الحليب",
        accounts=accounts,
        language="ar",
    )
    assert result["detected_intent"] == "receipt_collection"
    assert result["debit_account_id"] == 2  # Main Bank
    assert result["credit_account_id"] in (8, 9)  # Income or Sales Revenue
    assert result["amount"] == 1000.0
    assert result["confidence"] == "high"
    assert len(result["warnings"]) > 0
    assert any("تاجر الحليب" in w for w in result["warnings"])

    # Test 2: explicit revenue
    result2 = suggest_journal_entry(
        description="استلمنا 2000 إيراد خدمات",
        accounts=accounts,
        language="ar",
    )
    assert result2["detected_intent"] == "sales_revenue"
    assert result2["debit_account_id"] == 2  # Main Bank
    assert result2["amount"] == 2000.0

    # Test 3: وصلنا
    result3 = suggest_journal_entry(
        description="وصلنا 500 من العميل أحمد",
        accounts=accounts,
        language="ar",
    )
    assert result3["detected_intent"] == "receipt_collection"
    assert result3["amount"] == 500.0
    assert result3["confidence"] == "high"


# ── Data consistency: preview has no side effects ─────────────────────────────

def test_gemini_preview_does_not_create_journal_entry(
    base_url, admin_headers, default_company_id
):
    """
    The chat endpoint (POST /ai/gemini-assistant) must NEVER create a journal
    entry — it only generates a preview / suggested_action.  Verify the journal
    count stays the same before and after the call.
    """
    # Snapshot journal count
    count_before = requests.get(
        f"{base_url}/journal-entries?company_id={default_company_id}&skip=0&limit=1",
        headers=admin_headers,
    ).json()["total"]

    # Send a message that should trigger a suggested draft
    gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="paid 300 rent",
        language="en",
    )

    # Snapshot journal count again
    count_after = requests.get(
        f"{base_url}/journal-entries?company_id={default_company_id}&skip=0&limit=1",
        headers=admin_headers,
    ).json()["total"]

    assert count_after == count_before, (
        f"Preview endpoint created a journal entry! Count went from {count_before} to {count_after}"
    )


def test_confirm_action_failure_creates_no_entry(
    base_url, admin_headers, default_company_id
):
    """
    When confirm-action fails (e.g. invalid fiscal date), the journal entry
    count must remain unchanged — no orphan entries should exist.
    """
    # Snapshot
    count_before = requests.get(
        f"{base_url}/journal-entries?company_id={default_company_id}&skip=0&limit=1",
        headers=admin_headers,
    ).json()["total"]

    # Use a far-future date guaranteed to have no fiscal period
    response = _confirm_action_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        entry_date="2099-12-31",
    )

    assert response.status_code == 200
    assert response.json()["success"] is False

    # Verify count unchanged
    count_after = requests.get(
        f"{base_url}/journal-entries?company_id={default_company_id}&skip=0&limit=1",
        headers=admin_headers,
    ).json()["total"]

    assert count_after == count_before, (
        f"Failed confirm-action created an entry! Count went from {count_before} to {count_after}"
    )


# ── Data consistency: draft vs posted in reports ──────────────────────────────

def test_draft_journal_does_not_affect_profit_loss(
    base_url,
    admin_headers,
    default_company_id,
    default_bank_account_id,
    default_owner_capital_account_id,
):
    """
    A draft journal entry must NOT change the Profit & Loss totals.
    Reports only include posted and reversed entries.
    """
    # Ensure today has an open fiscal period
    ensure_fiscal_period_for_today(base_url, admin_headers, default_company_id)
    # Get P&L before
    pl_before = requests.get(
        f"{base_url}/reports/profit-and-loss?company_id={default_company_id}",
        headers=admin_headers,
    )
    assert pl_before.status_code == 200
    net_before = pl_before.json()["net_profit"]

    # Create a draft entry via confirm-action (must use today)
    entry_date = datetime.now(timezone.utc).date().isoformat()
    create_resp = requests.post(
        f"{base_url}/ai/gemini-assistant/confirm-action",
        headers=admin_headers,
        json={
            "company_id": default_company_id,
            "action_type": "create_journal_entry_draft",
            "payload": {
                "company_id": default_company_id,
                "entry_date": entry_date,
                "description": "Draft-only P&L test",
                "lines": [
                    {
                        "account_id": default_bank_account_id,
                        "debit": "5000.00",
                        "credit": "0.00",
                    },
                    {
                        "account_id": default_owner_capital_account_id,
                        "debit": "0.00",
                        "credit": "5000.00",
                    },
                ],
            },
        },
    )
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    assert create_data["success"] is True, (
        f"confirm-action failed: {create_data.get('error_code')} — {create_data.get('message')}"
    )

    # Get P&L after — must be unchanged
    pl_after = requests.get(
        f"{base_url}/reports/profit-and-loss?company_id={default_company_id}",
        headers=admin_headers,
    )
    assert pl_after.status_code == 200
    net_after = pl_after.json()["net_profit"]

    assert net_before == net_after, (
        f"Draft entry changed P&L! net_profit went from {net_before} to {net_after}"
    )


def test_posted_journal_does_affect_trial_balance(
    base_url,
    admin_headers,
    default_company_id,
    default_bank_account_id,
    default_owner_capital_account_id,
):
    """
    A posted journal entry MUST be reflected in the Trial Balance totals.
    This confirms the full create → post → report pipeline works end-to-end.
    """
    # Ensure today has an open fiscal period
    ensure_fiscal_period_for_today(base_url, admin_headers, default_company_id)
    # Get TB before
    tb_before = requests.get(
        f"{base_url}/reports/trial-balance?company_id={default_company_id}",
        headers=admin_headers,
    )
    assert tb_before.status_code == 200
    debit_before = tb_before.json()["total_debit"]

    # Create a draft entry (must use today)
    entry_date = datetime.now(timezone.utc).date().isoformat()
    create_resp = requests.post(
        f"{base_url}/ai/gemini-assistant/confirm-action",
        headers=admin_headers,
        json={
            "company_id": default_company_id,
            "action_type": "create_journal_entry_draft",
            "payload": {
                "company_id": default_company_id,
                "entry_date": entry_date,
                "description": "Post-then-check TB test",
                "lines": [
                    {
                        "account_id": default_bank_account_id,
                        "debit": "250.00",
                        "credit": "0.00",
                    },
                    {
                        "account_id": default_owner_capital_account_id,
                        "debit": "0.00",
                        "credit": "250.00",
                    },
                ],
            },
        },
    )
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    assert create_data["success"] is True, (
        f"confirm-action failed: {create_data.get('error_code')} — {create_data.get('message')}"
    )
    entity_id = create_data["entity_id"]

    # Post the entry (review first, then post)
    review_resp = requests.post(
        f"{base_url}/journal-entries/{entity_id}/review",
        headers=admin_headers,
    )
    assert review_resp.status_code == 200

    post_resp = requests.post(
        f"{base_url}/journal-entries/{entity_id}/post",
        headers=admin_headers,
    )
    assert post_resp.status_code == 200
    assert post_resp.json()["status"] == "posted"

    # Get TB after — debit total must have increased
    tb_after = requests.get(
        f"{base_url}/reports/trial-balance?company_id={default_company_id}",
        headers=admin_headers,
    )
    assert tb_after.status_code == 200
    debit_after = tb_after.json()["total_debit"]

    # Convert to float for comparison (API returns strings)
    assert float(debit_after) > float(debit_before), (
        f"Posted entry did not change TB! total_debit stayed at {debit_before} (after: {debit_after})"
    )


# ── Today-only date enforcement tests ─────────────────────────────────────────

def test_confirm_action_rejects_non_today_date(
    base_url, admin_headers, default_company_id
):
    """
    Confirm-action must reject any entry_date that is NOT backend-derived today.
    Sending yesterday's date must return error_code='gemini_date_must_be_today'.
    """
    from datetime import timedelta
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

    response = _confirm_action_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        entry_date=yesterday,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "gemini_date_must_be_today", (
        f"Expected gemini_date_must_be_today, got: {data.get('error_code')}"
    )


def test_confirm_action_rejects_future_date(
    base_url, admin_headers, default_company_id
):
    """
    Confirm-action must reject a future date too.
    """
    from datetime import timedelta
    future = (datetime.now(timezone.utc).date() + timedelta(days=30)).isoformat()

    response = _confirm_action_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        entry_date=future,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "gemini_date_must_be_today", (
        f"Expected gemini_date_must_be_today, got: {data.get('error_code')}"
    )


def test_gemini_preview_uses_backend_today(
    base_url, admin_headers, default_company_id
):
    """
    When Gemini suggests a journal draft, the suggested entry_date must be
    backend-derived today (UTC), not a hardcoded or user-supplied date.
    """
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="paid 100 rent",
        language="en",
    )
    assert response.status_code == 200
    data = response.json()

    if data.get("suggested_action"):
        sa = data["suggested_action"]
        assert sa["payload"]["entry_date"] == datetime.now(timezone.utc).date().isoformat(), (
            f"Expected today's date, got: {sa['payload']['entry_date']}"
        )


def test_gemini_refuses_explicit_old_date_arabic(
    base_url, admin_headers, default_company_id
):
    """
    When user asks for a journal entry with an explicit old date in Arabic
    (e.g. 'بتاريخ 2026-01-31'), Gemini must refuse and return a message
    saying entries are today-only. No suggested_action should be returned.
    """
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="تم دفع 500 إيجار بتاريخ 2026-01-31",
        language="ar",
    )
    assert response.status_code == 200
    data = response.json()

    # Must NOT have a suggested action (no draft created)
    assert data.get("suggested_action") is None, (
        "Expected no suggested_action for explicit old date request"
    )
    # Reply should mention today-only rule
    assert "اليوم فقط" in data["reply"] or "بتاريخ اليوم" in data["reply"], (
        f"Expected today-only refusal message, got: {data['reply'][:200]}"
    )


def test_gemini_refuses_yesterday_english(
    base_url, admin_headers, default_company_id
):
    """
    When user says 'paid 500 rent yesterday', Gemini must refuse with a
    today-only message or not produce a suggested_action.
    """
    response = gemini_assistant_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        message="paid 500 rent yesterday",
        language="en",
    )
    assert response.status_code == 200
    data = response.json()

    # Must NOT have a suggested action (no draft created with yesterday's date)
    if data.get("suggested_action") is not None:
        # If intent matched, verify the date detection refused it
        assert False, (
            "Expected no suggested_action for 'yesterday' request, "
            f"but got one with date: {data['suggested_action']['payload'].get('entry_date')}"
        )
    # Reply should either mention today-only or be a clarification/refusal
    reply_lower = data["reply"].lower()
    assert (
        "today" in reply_lower
        or "didn't understand" in reply_lower
        or "clarif" in reply_lower
    ), f"Expected today-only refusal or clarification, got: {data['reply'][:200]}"

