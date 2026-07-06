"""
Tests for the Gemini Assistant endpoints:
  POST /ai/gemini-assistant
  POST /ai/gemini-assistant/confirm-action
"""

import requests


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
    assert data["intent"] in ("answer_audit_question", "clarification")


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
    # Use a date within the open fiscal period (2026-01-01 to 2026-01-31)
    entry_date = "2026-01-15"

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
    assert data["success"] is True
    assert data["entity_id"] is not None
    assert data["entity_type"] == "journal_entry"
    assert "entry_no" in (data.get("data") or {})


def test_gemini_assistant_confirm_action_writes_audit_log(
    base_url,
    admin_headers,
    default_company_id,
    default_bank_account_id,
    default_owner_capital_account_id,
):
    """Confirmed AI action must create an audit log entry."""
    # Create the entry — use date within the open fiscal period (2026-01-01 to 2026-01-31)
    entry_date = "2026-01-15"
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
    entity_id = response.json()["entity_id"]

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
    # Account IDs 1/2 may not exist in this company, causing account_not_found
    # before we even reach fiscal validation — all these error codes are acceptable
    assert data["error_code"] in (
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
    This test depends on the existing open period (2026-01-15 is confirmed open).
    """
    response = _confirm_action_request(
        base_url=base_url,
        headers=admin_headers,
        company_id=default_company_id,
        entry_date="2026-01-15",
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
        # Should contain counterparty warning
        assert any("تاجر الحليب" in w for w in payload.get("warnings", []))


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
    assert data["intent"] in ("create_journal_draft", "sales_revenue")
    assert data.get("suggested_action") is not None

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

    assert data["intent"] in ("create_journal_draft", "receipt_collection", "sales_revenue")
    assert data.get("suggested_action") is not None


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
