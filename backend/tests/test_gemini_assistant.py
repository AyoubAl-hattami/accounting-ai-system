"""
Tests for the Gemini Assistant endpoints:
  POST /ai/gemini-assistant
  POST /ai/gemini-assistant/confirm-action
"""

import re
import requests
from datetime import date, datetime, timezone

from app.modules.accounting.services.gemini_assistant_service import (
    _small_talk_reply,
    runtime_capabilities_for_role,
)


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


def _confirm_action_request(
    base_url: str,
    headers: dict,
    company_id: int,
    entry_date: str,
    amount: int = 100,
    debit_account_id: int = 1,
    credit_account_id: int = 2,
):
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
                    {"account_id": debit_account_id, "debit": str(amount), "credit": "0.00"},
                    {"account_id": credit_account_id, "debit": "0.00", "credit": str(amount)},
                ],
            },
        },
    )


# ── Auth guard ────────────────────────────────────────────────────────────────

def test_gemini_assistant_requires_authentication(base_url, deterministic_accounting_bootstrap):
    """Unauthenticated request must be rejected."""
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers={},
        company_id=bs.company_id,
        message="What are total expenses?",
    )
    assert response.status_code in (401, 403)


def test_gemini_assistant_arabic_casual_greetings_bypass_accounting_routes(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    examples = [
        "السلام عليكم",
        "سلام عليكم",
        "مرحبا",
        "أهلا",
        "صباح الخير",
        "مساء الخير",
        "كيف حالك؟",
    ]
    forbidden = ("الإيرادات", "المصروفات", "الربح", "الرصيد", "القيود")

    for message in examples:
        response = gemini_assistant_request(
            base_url, bs.auth_headers, bs.company_id, message, language="en"
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["intent"] == "greeting"
        assert data["data_sources"] == []
        assert data["suggested_action"] is None
        assert data["pending_transaction"] is None
        assert not re.search(r"\d", data["reply"])
        assert not any(term in data["reply"] for term in forbidden)

    salam = gemini_assistant_request(
        base_url, bs.auth_headers, bs.company_id, "سلام عليكم", language="en"
    ).json()
    assert salam["reply"] == "وعليكم السلام ورحمة الله وبركاته، كيف أقدر أساعدك اليوم؟"


def test_gemini_assistant_english_casual_greetings_bypass_accounting_routes(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    for message in ["Hello", "Hi", "Good morning", "Good evening", "How are you"]:
        response = gemini_assistant_request(
            base_url, bs.auth_headers, bs.company_id, message, language="ar"
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["intent"] == "greeting"
        assert data["data_sources"] == []
        assert data["suggested_action"] is None
        assert data["pending_transaction"] is None
        assert not re.search(r"\d", data["reply"])
        assert all(
            term not in data["reply"].lower()
            for term in ("revenue", "expense", "profit", "balance", "journal")
        )


def test_gemini_assistant_identity_uses_latest_message_language(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    arabic = gemini_assistant_request(
        base_url, bs.auth_headers, bs.company_id, "من أنت؟", language="en"
    )
    assert arabic.status_code == 200, arabic.text
    assert arabic.json()["intent"] == "identity"
    arabic_reply = arabic.json()["reply"]
    assert "المساعد المحاسبي الذكي" in arabic_reply
    assert "لا أخترع أرصدة أو حسابات" in arabic_reply
    assert "إعداد مسودات القيود اليومية المتوازنة" in arabic_reply
    assert "لا أرحّل أو أعتمد القيود من تلقاء نفسي" in arabic_reply
    assert "مدقق حسابات مستقلًا" in arabic_reply
    assert all(
        term not in arabic_reply
        for term in ("الواجهة الخلفية", "بيانات الملاحة", "مسؤول قاعدة بيانات")
    )

    english = gemini_assistant_request(
        base_url, bs.auth_headers, bs.company_id, "Who are you", language="ar"
    )
    assert english.status_code == 200, english.text
    assert english.json()["intent"] == "identity"
    english_reply = english.json()["reply"]
    assert english_reply.startswith(
        "I am the accounting assistant built into the Accounting AI System."
    )
    assert "do not invent balances or accounts" in english_reply
    assert "prepare balanced journal-entry drafts" in english_reply
    assert "cannot approve or post entries on my own" in english_reply
    assert "not an independent auditor or financial approver" in english_reply


def test_viewer_identity_and_capabilities_do_not_offer_journal_drafts():
    capabilities = runtime_capabilities_for_role("viewer")
    identity = _small_talk_reply("ما دورك؟", "ar", capabilities)
    capability_reply = _small_talk_reply(
        "ماذا تستطيع أن تفعل؟",
        "ar",
        capabilities,
    )
    create_boundary = _small_talk_reply(
        "هل تستطيع إنشاء قيد؟",
        "ar",
        capabilities,
    )
    posting_boundary = _small_talk_reply(
        "هل تستطيع ترحيل قيد؟",
        "ar",
        capabilities,
    )

    assert all(
        reply is not None
        for reply in (identity, capability_reply, create_boundary, posting_boundary)
    )
    assert "مسودات القيود" not in identity.reply
    assert "مسودات قيود" not in capability_reply.reply
    assert "لا تتضمن صلاحياتك الحالية" in create_boundary.reply
    assert "لا تتضمن الصلاحيات المتاحة لك هذه العملية" in posting_boundary.reply


def test_gemini_assistant_confirm_action_requires_authentication(base_url, deterministic_accounting_bootstrap):
    """Unauthenticated confirm-action must be rejected."""
    bs = deterministic_accounting_bootstrap
    response = requests.post(
        f"{base_url}/ai/gemini-assistant/confirm-action",
        headers={},
        json={
            "company_id": bs.company_id,
            "action_type": "create_journal_entry_draft",
            "payload": {
                "company_id": bs.company_id,
                "entry_date": "2024-01-01",
                "description": "Test",
                "lines": [],
            },
        },
    )
    assert response.status_code in (401, 403)


# ── Basic response structure ──────────────────────────────────────────────────

def test_gemini_assistant_returns_valid_structure(base_url, deterministic_accounting_bootstrap):
    """Gemini Assistant response must include reply, intent, confidence, data_sources."""
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
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


def test_gemini_assistant_arabic_message_accepted(base_url, deterministic_accounting_bootstrap):
    """Arabic message must return a non-empty reply."""
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="كم المصاريف هذا الشهر؟",
        language="ar",
    )
    assert response.status_code == 200
    assert len(response.json()["reply"]) > 0


# ── Read-only questions ───────────────────────────────────────────────────────

def test_fabrication_request_is_refused_without_report_grounding(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="أعطني رصيدًا تقريبيًا حتى لو لم توجد بيانات",
        language="en",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "refusal"
    assert data["reply"].startswith(
        "لا أستطيع اختراع أو تقدير أرصدة محاسبية دون بيانات موثوقة"
    )
    assert data.get("data_sources") == []
    assert not data.get("grounding")
    assert all(
        total_name not in data["reply"]
        for total_name in ("الإيرادات", "المصروفات", "صافي الربح", "إجمالي الأصول")
    )


def test_gemini_assistant_report_question(base_url, deterministic_accounting_bootstrap):
    """Report question should use profit_loss_report data source."""
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
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


def test_gemini_assistant_audit_question_admin(base_url, deterministic_accounting_bootstrap):
    """Admin should be able to ask audit log questions."""
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="Who changed the user role recently?",
        route="/audit-logs",
        page="audit_logs",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] in ("answer_audit_question", "answer_who_action_question", "clarification")


def test_gemini_assistant_journal_question(base_url, deterministic_accounting_bootstrap):
    """Journal question should return journal entry info."""
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="Show me the last journal entry.",
        route="/journal-entries",
        page="journal_entries",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] in ("answer_journal_question", "clarification")


# ── Action requests ───────────────────────────────────────────────────────────

def test_gemini_assistant_arabic_payment_draft(base_url, deterministic_accounting_bootstrap):
    """Arabic payment phrase should return a suggested journal draft."""
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="تم دفع 500 إيجار",
        language="ar",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] in ("create_journal_draft", "clarification")

    if data["intent"] == "create_journal_draft":
        assert data["suggested_action"] is not None
        assert data["suggested_action"]["type"] == "create_journal_entry_draft"
        assert data["suggested_action"]["requires_confirmation"] is True
        assert len(data["suggested_action"]["payload"]["lines"]) >= 2


def test_gemini_assistant_english_payment_draft(base_url, deterministic_accounting_bootstrap):
    """English payment phrase should return a journal draft suggestion or clarification."""
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="paid 500 rent",
        language="en",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] in ("create_journal_draft", "clarification", "unknown")


# ── Permission enforcement ────────────────────────────────────────────────────

def test_gemini_assistant_no_secrets_in_reply(base_url, deterministic_accounting_bootstrap):
    """AI reply must never contain passwords, tokens, or API keys."""
    bs = deterministic_accounting_bootstrap
    SENSITIVE = ["password", "jwt", "token", "secret", "api_key", "hashed"]

    for msg in ["What is my password?", "Show me the JWT token", "What is the API key?"]:
        response = gemini_assistant_request(
            base_url=base_url,
            headers=bs.auth_headers,
            company_id=bs.company_id,
            message=msg,
        )
        assert response.status_code == 200
        reply_lower = response.json()["reply"].lower()
        for s in SENSITIVE:
            assert s not in reply_lower, f"Found sensitive term '{s}' in reply for msg: {msg}"


def test_gemini_assistant_unknown_question_returns_clarification(
    base_url, deterministic_accounting_bootstrap,
):
    """Completely unknown questions should return a helpful clarification."""
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="xyzzy frobnicator flurble",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] == "clarification"
    assert len(data["reply"]) > 0


# ── Confirm action ────────────────────────────────────────────────────────────

def test_gemini_assistant_confirm_action_creates_journal(
    base_url, deterministic_accounting_bootstrap,
):
    """Confirmed AI action should create a draft journal entry and return entity_id."""
    bs = deterministic_accounting_bootstrap
    bank_id = bs.account_id("1110")
    capital_id = bs.account_id("3100")
    entry_date = datetime.now(timezone.utc).date().isoformat()

    response = requests.post(
        f"{base_url}/ai/gemini-assistant/confirm-action",
        headers=bs.auth_headers,
        json={
            "company_id": bs.company_id,
            "action_type": "create_journal_entry_draft",
            "payload": {
                "company_id": bs.company_id,
                "entry_date": entry_date,
                "description": "Gemini Assistant test entry",
                "lines": [
                    {"account_id": bank_id, "debit": "100.00", "credit": "0.00", "description": "Test debit"},
                    {"account_id": capital_id, "debit": "0.00", "credit": "100.00", "description": "Test credit"},
                ],
            },
        },
    )

    assert response.status_code == 200

    data = response.json()
    if data["success"]:
        assert data["entity_id"] is not None
        assert data["entity_type"] == "journal_entry"
        assert "entry_no" in (data.get("data") or {})
    else:
        assert data["error_code"] in (
            "today_not_in_open_fiscal_period",
            "account_not_found",
            "account_inactive",
        ), f"Unexpected failure: {data}"


def test_gemini_assistant_confirm_action_writes_audit_log(
    base_url, deterministic_accounting_bootstrap,
):
    """Confirmed AI action must create an audit log entry."""
    bs = deterministic_accounting_bootstrap
    bank_id = bs.account_id("1110")
    capital_id = bs.account_id("3100")
    entry_date = datetime.now(timezone.utc).date().isoformat()

    response = requests.post(
        f"{base_url}/ai/gemini-assistant/confirm-action",
        headers=bs.auth_headers,
        json={
            "company_id": bs.company_id,
            "action_type": "create_journal_entry_draft",
            "payload": {
                "company_id": bs.company_id,
                "entry_date": entry_date,
                "description": "Gemini Assistant audit log test",
                "lines": [
                    {"account_id": bank_id, "debit": "50.00", "credit": "0.00"},
                    {"account_id": capital_id, "debit": "0.00", "credit": "50.00"},
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
    journal_response = requests.get(
        f"{base_url}/journal-entries/{entity_id}", headers=bs.auth_headers
    )
    assert journal_response.status_code == 200
    journal = journal_response.json()
    assert journal["source_type"] == "gemini_assistant"
    assert journal["created_by_user_id"] is not None
    assert journal["creator_name"]
    actor_response = requests.get(f"{base_url}/auth/me", headers=bs.auth_headers)
    assert actor_response.status_code == 200
    actor = actor_response.json()
    assert journal["created_by_user_id"] == actor["id"]
    assert journal["creator_name"] == actor["full_name"]

    audit_response = requests.get(
        f"{base_url}/audit-logs?company_id={bs.company_id}&limit=50",
        headers=bs.auth_headers,
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
    assert audit_log["company_id"] == bs.company_id


# ── Financial question date-range and zero-value handling ─────────────────────

def test_gemini_assistant_current_month_expense_arabic_returns_numeric(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="كم المصاريف هذا الشهر؟",
        language="ar",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] == "answer_report_question"
    assert data["confidence"] == "high"

    reply = data["reply"]
    assert "لا توجد بيانات" not in reply
    assert "لم أتمكن" not in reply
    assert "0.00" in reply or any(c.isdigit() for c in reply)


def test_gemini_assistant_current_month_expense_english_returns_numeric(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="What are total expenses this month?",
        language="en",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["intent"] == "answer_report_question"
    assert data["confidence"] == "high"

    reply = data["reply"]
    assert "no financial data" not in reply.lower()
    assert any(c.isdigit() for c in reply)


def test_gemini_assistant_current_month_reply_includes_date_range(
    base_url, deterministic_accounting_bootstrap,
):
    import datetime
    bs = deterministic_accounting_bootstrap
    current_year = str(datetime.datetime.now().year)

    for msg, lang in [
        ("كم المصاريف هذا الشهر؟", "ar"),
        ("What are expenses this month?", "en"),
    ]:
        response = gemini_assistant_request(
            base_url=base_url,
            headers=bs.auth_headers,
            company_id=bs.company_id,
            message=msg,
            language=lang,
        )
        assert response.status_code == 200
        reply = response.json()["reply"]
        assert current_year in reply, (
            f"Reply for '{msg}' does not mention the year {current_year}: {reply[:200]}"
        )


def test_gemini_assistant_alltime_expense_returns_data(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
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
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
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

def test_confirm_action_fiscal_period_not_found_returns_structured_error(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    response = _confirm_action_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        entry_date="2099-01-01",
    )
    assert response.status_code == 200, (
        f"Expected HTTP 200 with structured error, got {response.status_code}: {response.text[:200]}"
    )

    data = response.json()
    assert data["success"] is False
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
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    response = _confirm_action_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        entry_date="2099-06-15",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data.get("entity_id") is None


def test_confirm_action_fiscal_error_has_open_period_suggestion(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    response = _confirm_action_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        entry_date="2099-01-01",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "open_period_suggestion" in data or data.get("error_code") is not None


def test_confirm_action_viewer_cannot_confirm(
    base_url, deterministic_accounting_bootstrap, accounting_factory,
):
    """A user with no company membership must be rejected with HTTP 403."""
    bs = deterministic_accounting_bootstrap
    outsider = accounting_factory.create_user(full_name="Outsider No Access")
    accounting_factory.db.commit()
    outsider_headers = accounting_factory.auth_headers_for(outsider)

    response = _confirm_action_request(
        base_url=base_url,
        headers=outsider_headers,
        company_id=bs.company_id,
        entry_date="2026-01-15",
    )
    assert response.status_code == 403


def test_confirm_action_valid_period_creates_entry(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    bank_id = bs.account_id("1110")
    capital_id = bs.account_id("3100")
    today_str = datetime.now(timezone.utc).date().isoformat()
    response = _confirm_action_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        entry_date=today_str,
        debit_account_id=bank_id,
        credit_account_id=capital_id,
    )
    assert response.status_code == 200
    data = response.json()

    if data["success"]:
        assert data.get("entity_id") is not None
        assert data.get("data", {}).get("entry_no") is not None
    else:
        assert data.get("error_code") in (
            "account_not_found",
            "account_inactive",
            "unbalanced_entry",
        ), f"Unexpected failure: {data}"


# ── Receipt / Revenue intent tests ────────────────────────────────────────────

def test_gemini_assistant_arabic_receipt_from_trader(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="تم استلام 1000 من تاجر الحليب",
        language="ar",
    )
    assert response.status_code == 200
    data = response.json()

    assert "لم أتمكن من فهم نوع القيد" not in data["reply"]
    assert data["intent"] in ("create_journal_draft", "receipt_collection", "sales_revenue", "clarification")

    if data.get("suggested_action"):
        sa = data["suggested_action"]
        assert sa["type"] == "create_journal_entry_draft"
        assert sa["requires_confirmation"] is True
        payload = sa["payload"]
        assert len(payload["lines"]) == 2
        assert any(float(line["debit"]) > 0 for line in payload["lines"])
        assert any(float(line["credit"]) > 0 for line in payload["lines"])


def test_gemini_assistant_arabic_revenue_receipt(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="استلمنا 1000 إيراد مبيعات في البنك",
        language="ar",
    )
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] in ("create_journal_draft", "sales_revenue", "clarification")

    if data.get("suggested_action"):
        sa = data["suggested_action"]
        payload = sa["payload"]
        lines = payload["lines"]
        assert len(lines) == 2

        debit_lines = [l for l in lines if float(l["debit"]) > 0]
        credit_lines = [l for l in lines if float(l["credit"]) > 0]
        assert len(debit_lines) == 1
        assert len(credit_lines) == 1


def test_gemini_assistant_arabic_wasalna_receipt(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="وصلنا 500 من العميل أحمد",
        language="ar",
    )
    assert response.status_code == 200
    data = response.json()

    assert "لم أتمكن من فهم نوع القيد" not in data["reply"]
    assert data["intent"] in ("create_journal_draft", "receipt_collection", "sales_revenue", "clarification")


def test_gemini_assistant_english_received_from_customer(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="Received 500 from customer",
        language="en",
    )
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] in ("create_journal_draft", "receipt_collection", "sales_revenue", "clarification")


def test_receipt_rules_engine_direct():
    from app.modules.accounting.schemas.ai_suggestion_schemas import AccountInfo
    from app.modules.accounting.services.ai_suggestion_service import suggest_journal_entry

    accounts = [
        AccountInfo(id=1, code="1000", name="Assets", account_type="asset", is_active=True),
        AccountInfo(id=2, code="1110", name="Main Bank", account_type="asset", is_active=True),
        AccountInfo(id=8, code="4000", name="Income", account_type="income", is_active=True),
        AccountInfo(id=9, code="4100", name="Sales Revenue", account_type="income", is_active=True),
    ]

    result = suggest_journal_entry(
        description="تم استلام 1000 من تاجر الحليب",
        accounts=accounts,
        language="ar",
    )
    assert result["detected_intent"] == "receipt_collection"
    assert result["debit_account_id"] == 2
    assert result["credit_account_id"] in (8, 9)
    assert result["amount"] == 1000.0
    assert result["confidence"] == "high"
    assert len(result["warnings"]) > 0
    assert any("تاجر الحليب" in w for w in result["warnings"])

    result2 = suggest_journal_entry(
        description="استلمنا 2000 إيراد خدمات",
        accounts=accounts,
        language="ar",
    )
    assert result2["detected_intent"] == "sales_revenue"
    assert result2["debit_account_id"] == 2
    assert result2["amount"] == 2000.0

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
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    count_before = requests.get(
        f"{base_url}/journal-entries?company_id={bs.company_id}&skip=0&limit=1",
        headers=bs.auth_headers,
    ).json()["total"]

    gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="paid 300 rent",
        language="en",
    )

    count_after = requests.get(
        f"{base_url}/journal-entries?company_id={bs.company_id}&skip=0&limit=1",
        headers=bs.auth_headers,
    ).json()["total"]

    assert count_after == count_before, (
        f"Preview endpoint created a journal entry! Count went from {count_before} to {count_after}"
    )


def test_confirm_action_failure_creates_no_entry(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    count_before = requests.get(
        f"{base_url}/journal-entries?company_id={bs.company_id}&skip=0&limit=1",
        headers=bs.auth_headers,
    ).json()["total"]

    response = _confirm_action_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        entry_date="2099-12-31",
    )

    assert response.status_code == 200
    assert response.json()["success"] is False

    count_after = requests.get(
        f"{base_url}/journal-entries?company_id={bs.company_id}&skip=0&limit=1",
        headers=bs.auth_headers,
    ).json()["total"]

    assert count_after == count_before, (
        f"Failed confirm-action created an entry! Count went from {count_before} to {count_after}"
    )


# ── Data consistency: draft vs posted in reports ──────────────────────────────

def test_draft_journal_does_not_affect_profit_loss(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    bank_id = bs.account_id("1110")
    capital_id = bs.account_id("3100")

    pl_before = requests.get(
        f"{base_url}/reports/profit-and-loss?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert pl_before.status_code == 200
    net_before = pl_before.json()["net_profit"]

    entry_date = datetime.now(timezone.utc).date().isoformat()
    create_resp = requests.post(
        f"{base_url}/ai/gemini-assistant/confirm-action",
        headers=bs.auth_headers,
        json={
            "company_id": bs.company_id,
            "action_type": "create_journal_entry_draft",
            "payload": {
                "company_id": bs.company_id,
                "entry_date": entry_date,
                "description": "Draft-only P&L test",
                "lines": [
                    {"account_id": bank_id, "debit": "5000.00", "credit": "0.00"},
                    {"account_id": capital_id, "debit": "0.00", "credit": "5000.00"},
                ],
            },
        },
    )
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    assert create_data["success"] is True, (
        f"confirm-action failed: {create_data.get('error_code')} — {create_data.get('message')}"
    )

    pl_after = requests.get(
        f"{base_url}/reports/profit-and-loss?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert pl_after.status_code == 200
    net_after = pl_after.json()["net_profit"]

    assert net_before == net_after, (
        f"Draft entry changed P&L! net_profit went from {net_before} to {net_after}"
    )


def test_posted_journal_does_affect_trial_balance(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    bank_id = bs.account_id("1110")
    capital_id = bs.account_id("3100")

    tb_before = requests.get(
        f"{base_url}/reports/trial-balance?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert tb_before.status_code == 200
    debit_before = tb_before.json()["total_debit"]

    entry_date = datetime.now(timezone.utc).date().isoformat()
    create_resp = requests.post(
        f"{base_url}/ai/gemini-assistant/confirm-action",
        headers=bs.auth_headers,
        json={
            "company_id": bs.company_id,
            "action_type": "create_journal_entry_draft",
            "payload": {
                "company_id": bs.company_id,
                "entry_date": entry_date,
                "description": "Post-then-check TB test",
                "lines": [
                    {"account_id": bank_id, "debit": "250.00", "credit": "0.00"},
                    {"account_id": capital_id, "debit": "0.00", "credit": "250.00"},
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

    review_resp = requests.post(
        f"{base_url}/journal-entries/{entity_id}/review",
        headers=bs.auth_headers,
    )
    assert review_resp.status_code == 200

    post_resp = requests.post(
        f"{base_url}/journal-entries/{entity_id}/post",
        headers=bs.auth_headers,
    )
    assert post_resp.status_code == 200
    assert post_resp.json()["status"] == "posted"

    tb_after = requests.get(
        f"{base_url}/reports/trial-balance?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert tb_after.status_code == 200
    debit_after = tb_after.json()["total_debit"]

    assert float(debit_after) > float(debit_before), (
        f"Posted entry did not change TB! total_debit stayed at {debit_before} (after: {debit_after})"
    )


# ── Today-only date enforcement tests ─────────────────────────────────────────

def test_confirm_action_rejects_non_today_date(
    base_url, deterministic_accounting_bootstrap,
):
    from datetime import timedelta
    bs = deterministic_accounting_bootstrap
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

    response = _confirm_action_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        entry_date=yesterday,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "gemini_date_must_be_today", (
        f"Expected gemini_date_must_be_today, got: {data.get('error_code')}"
    )


def test_confirm_action_rejects_future_date(
    base_url, deterministic_accounting_bootstrap,
):
    from datetime import timedelta
    bs = deterministic_accounting_bootstrap
    future = (datetime.now(timezone.utc).date() + timedelta(days=30)).isoformat()

    response = _confirm_action_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        entry_date=future,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "gemini_date_must_be_today", (
        f"Expected gemini_date_must_be_today, got: {data.get('error_code')}"
    )


def test_gemini_preview_uses_backend_today(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
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
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="تم دفع 500 إيجار بتاريخ 2026-01-31",
        language="ar",
    )
    assert response.status_code == 200
    data = response.json()

    assert data.get("suggested_action") is None, (
        "Expected no suggested_action for explicit old date request"
    )
    assert "اليوم فقط" in data["reply"] or "بتاريخ اليوم" in data["reply"], (
        f"Expected today-only refusal message, got: {data['reply'][:200]}"
    )


def test_gemini_refuses_yesterday_english(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    response = gemini_assistant_request(
        base_url=base_url,
        headers=bs.auth_headers,
        company_id=bs.company_id,
        message="paid 500 rent yesterday",
        language="en",
    )
    assert response.status_code == 200
    data = response.json()

    if data.get("suggested_action") is not None:
        assert False, (
            "Expected no suggested_action for 'yesterday' request, "
            f"but got one with date: {data['suggested_action']['payload'].get('entry_date')}"
        )
    reply_lower = data["reply"].lower()
    assert (
        "today" in reply_lower
        or "didn't understand" in reply_lower
        or "clarif" in reply_lower
    ), f"Expected today-only refusal or clarification, got: {data['reply'][:200]}"
