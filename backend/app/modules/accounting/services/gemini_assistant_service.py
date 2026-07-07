"""
Gemini Assistant Service.

Architecture:
  1. Internal tools collect real company data (P&L, audit logs, journal entries, etc.)
  2. Data is summarised into a safe context string (no secrets, no tokens)
  3. Context + user question are sent to Gemini for a natural language answer
  4. Fallback: if Gemini is not configured or fails → deterministic rules-based answers
  5. Action requests (create journal) always use the rules engine, NEVER Gemini execution

Role enforcement:
  - All data tools are company-scoped (company_id always applied)
  - Role checks happen before any data is fetched
  - Sensitive fields (password_hash, token, etc.) are stripped before any processing

Confirmed write actions (create_journal_entry_draft) are handled in ai_routes.py,
not here — this service only returns SuggestedAction payloads for confirmation.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.clock import get_today_date
from app.modules.accounting.schemas.gemini_assistant_schemas import (
    GeminiAssistantReply,
    PageContext,
    SuggestedAction,
    SuggestedJournalLine,
    SuggestedJournalPayload,
)
from app.modules.accounting.services.audit_service import list_audit_logs
from app.modules.accounting.services.report_service import get_profit_and_loss
from app.modules.accounting.services.account_service import list_accounts
from app.modules.accounting.services.journal_service import (
    list_journal_entries,
    count_journal_entries,
)
from app.modules.accounting.services.company_user_service import list_company_users
from app.modules.accounting.services.ai_suggestion_service import suggest_journal_entry

logger = logging.getLogger(__name__)


# ── Sensitive field guard ─────────────────────────────────────────────────────

_SENSITIVE = frozenset({
    "password", "password_hash", "hashed_password",
    "token", "raw_token", "invite_token", "jwt",
    "secret", "api_key", "access_token", "refresh_token",
    "reset_token", "verification_token",
})


def _scrub(d: dict) -> dict:
    """Remove sensitive keys from a dict (shallow)."""
    return {k: v for k, v in d.items() if k.lower() not in _SENSITIVE}


# ── Role permission matrix ────────────────────────────────────────────────────

_CAN_READ_REPORTS = frozenset({"admin", "accountant", "reviewer", "approver", "auditor", "viewer"})
_CAN_READ_AUDIT_LOGS = frozenset({"admin", "auditor"})
_CAN_READ_USERS = frozenset({"admin", "auditor"})
_CAN_CREATE_DRAFT = frozenset({"admin", "accountant"})


# ── Internal data tools ───────────────────────────────────────────────────────

def _tool_get_profit_loss(
    db: Session,
    company_id: int,
    start_date: date | None,
    end_date: date | None,
) -> dict:
    """
    Always returns a dict with numeric totals (0.0 if no data).
    Never returns {} — callers rely on the structure being present.
    """
    try:
        report = get_profit_and_loss(
            db=db, company_id=company_id,
            start_date=start_date, end_date=end_date,
        )
        return {
            "total_revenue": float(report.total_revenue),
            "total_expenses": float(report.total_expenses),
            "net_profit": float(report.net_profit),
            "has_data": bool(report.lines),  # True if there are any account lines
            "revenue_lines": [
                {"name": l.account_name, "amount": float(l.net_amount)}
                for l in report.lines
                if l.account_type == "income" and float(l.net_amount) != 0
            ][:10],
            "expense_lines": [
                {"name": l.account_name, "amount": float(l.net_amount)}
                for l in report.lines
                if l.account_type == "expense" and float(l.net_amount) != 0
            ][:10],
        }
    except Exception as exc:
        logger.warning("_tool_get_profit_loss failed: %s", exc)
        # Return zero-valued dict so callers always have a valid structure
        return {
            "total_revenue": 0.0,
            "total_expenses": 0.0,
            "net_profit": 0.0,
            "has_data": False,
            "revenue_lines": [],
            "expense_lines": [],
            "error": str(exc),
        }


def _tool_get_recent_journal_entries(db: Session, company_id: int, limit: int = 5) -> list[dict]:
    try:
        entries = list_journal_entries(db=db, company_id=company_id, limit=limit)
        return [
            {
                "entry_no": e.entry_no,
                "entry_date": str(e.entry_date),
                "description": e.description,
                "status": e.status,
                "total_debit": float(sum(l.debit for l in e.lines)),
            }
            for e in entries
        ]
    except Exception:
        return []


def _tool_get_recent_audit_logs(
    db: Session,
    company_id: int,
    action: str | None = None,
    limit: int = 10,
) -> list[dict]:
    try:
        logs = list_audit_logs(db=db, company_id=company_id, action=action, limit=limit)
        result = []
        for log in logs:
            entry = {
                "action": log.action,
                "actor": log.actor_name or log.actor_email or log.actor,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "created_at": log.created_at.isoformat()[:19] if log.created_at else None,
                "description": log.description,
            }
            if log.new_values:
                entry["new_values"] = _scrub(log.new_values)
            result.append(entry)
        return result
    except Exception:
        return []


def _tool_get_company_users(db: Session, company_id: int) -> list[dict]:
    try:
        users = list_company_users(db=db, company_id=company_id)
        return [
            {
                "role": u.role,
                "is_active": u.is_active,
                "name": u.user.full_name if hasattr(u, "user") and u.user else None,
                "email": u.user.email if hasattr(u, "user") and u.user else None,
            }
            for u in users
        ]
    except Exception:
        return []


def _tool_get_accounts(db: Session, company_id: int) -> list[dict]:
    try:
        accounts = list_accounts(db=db, company_id=company_id, limit=500)
        return [
            {"id": a.id, "code": a.code, "name": a.name,
             "account_type": a.account_type, "is_active": a.is_active}
            for a in accounts
        ]
    except Exception:
        return []


# ── Intent classification (deterministic) ────────────────────────────────────

def _classify_intent(message: str) -> str:
    text = message.strip()
    text_lower = text.lower()

    # Action-creation signals (must check first)
    action_arabic = any(phrase in text for phrase in [
        "تم دفع", "تم استلام", "دفعنا", "استلمنا", "سجل قيد",
        "اسجل قيد", "إضافة قيد", "أضف قيد", "سجل مصروف",
        "وصلنا", "قبضنا", "تم تحصيل", "استلام مبلغ", "دخل البنك",
    ])
    action_english = bool(re.search(
        r"\b(paid|pay|record a|add a|create a|register a|received|collected)\b",
        text, re.IGNORECASE,
    ))
    if action_arabic or action_english:
        return "action_request"

    # Report / financial questions
    if any(t in text_lower for t in [
        "profit", "loss", "revenue", "income", "expense", "expenses",
        "ربح", "خسارة", "إيراد", "ايراد", "مصروف", "مصاريف",
        "how much", "كم", "total", "إجمالي", "اجمالي",
    ]):
        return "report_question"

    # Balance questions
    if any(t in text_lower for t in [
        "balance", "trial balance", "balance sheet",
        "رصيد", "ميزانية", "ميزان المراجعة",
    ]):
        return "balance_question"

    # Audit / history
    if any(t in text_lower for t in [
        "who", "من", "changed", "عدل", "modified", "غير",
        "audit", "history", "log", "last activity", "آخر نشاط",
        "who posted", "من رحّل", "who reviewed", "من راجع",
        "who changed", "من غير", "who created", "من أنشأ",
        "permission", "صلاحية", "role change",
    ]):
        return "audit_question"

    # Journal entry questions
    if any(t in text_lower for t in [
        "journal", "entry", "entries", "قيد", "قيود",
        "last entry", "آخر قيد", "draft", "مسودة",
    ]):
        return "journal_question"

    # User questions
    if any(t in text_lower for t in [
        "user", "users", "مستخدم", "مستخدمين",
        "inactive", "معطل", "active users", "member", "أعضاء",
    ]):
        return "user_question"

    return "unknown"


# ── Temporal date-range extraction from message ───────────────────────────────

def _extract_date_range(
    message: str,
    page_start: date | None,
    page_end: date | None,
) -> tuple[date | None, date | None, str]:
    """
    Resolve the date range for a financial question.
    Priority:
      1. Page-context filters (if frontend passes dates, respect them)
      2. Temporal keywords in the message (this month, this year, etc.)
      3. None/None = all-time (no filter)

    Returns: (start_date, end_date, period_label)
    """
    import calendar

    # If the frontend already gave us explicit dates, use them
    if page_start and page_end:
        return page_start, page_end, f"{page_start} – {page_end}"

    text = message.lower()
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month

    # Detect "this month" / "هذا الشهر" / "الشهر الحالي"
    THIS_MONTH_SIGNALS = [
        "this month", "هذا الشهر", "الشهر الحالي", "الشهر الجاري",
        "current month", "this month's", "شهريا",
    ]
    if any(s in text for s in THIS_MONTH_SIGNALS):
        last_day = calendar.monthrange(year, month)[1]
        start = date(year, month, 1)
        end = date(year, month, last_day)
        label = f"{start} – {end}"
        return start, end, label

    # Detect "this year" / "هذا العام" / "العام الحالي"
    THIS_YEAR_SIGNALS = [
        "this year", "هذا العام", "العام الحالي", "السنة الحالية",
        "current year", "this year's",
    ]
    if any(s in text for s in THIS_YEAR_SIGNALS):
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        label = f"{start} – {end}"
        return start, end, label

    # Detect "last month" / "الشهر الماضي"
    LAST_MONTH_SIGNALS = [
        "last month", "الشهر الماضي", "الشهر السابق",
    ]
    if any(s in text for s in LAST_MONTH_SIGNALS):
        if month == 1:
            lm_year, lm_month = year - 1, 12
        else:
            lm_year, lm_month = year, month - 1
        last_day = calendar.monthrange(lm_year, lm_month)[1]
        start = date(lm_year, lm_month, 1)
        end = date(lm_year, lm_month, last_day)
        label = f"{start} – {end}"
        return start, end, label

    # Detect "all time" / "إجمالاً" / "كل"
    ALL_TIME_SIGNALS = [
        "all time", "all-time", "overall", "total", "everything",
        "إجمالاً", "إجمالياً", "إجمالي ال",
        "كل ال", "كل المصاريف", "كل الإيرادات",
    ]
    if any(s in text for s in ALL_TIME_SIGNALS):
        return None, None, "all time"

    # Default: no date filter = all available data
    return None, None, "all available data"


# ── Gemini assistant call ──────────────────────────────────────────────────────

def _call_gemini_for_answer(
    question: str,
    context_summary: str,
    language: str,
) -> str | None:
    """
    Send a context + question to Gemini and return a natural language answer.
    Returns None if Gemini is not configured or fails (caller falls back to rules).
    Never sends secrets, keys, or tokens to Gemini.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "").strip()
    model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash").strip()

    if not api_key:
        return None

    lang_instruction = (
        "أجب باللغة العربية فقط." if language == "ar"
        else "Respond in English only."
    )

    prompt = f"""You are a professional accounting assistant for a business accounting system.
You have been given a summary of the company's financial data below.
Answer the user's question using ONLY the provided data — do not invent numbers.
IMPORTANT RULES:
- If the data shows 0.00 for any value, state it as 0.00. Do NOT say 'no data available'.
- Always mention the exact date range from the context in your answer.
- If the note says 'No posted journal entries found', state the amount is 0.00 for that period and explain briefly.
- Keep the answer concise and professional.
- Do NOT mention any passwords, tokens, API keys, or internal system details.
{lang_instruction}

=== Company Financial Context ===
{context_summary}

=== User Question ===
{question}

Answer:"""

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=prompt)
        text = (response.text or "").strip()
        return text if text else None
    except Exception as exc:
        logger.warning("Gemini assistant call failed: %s", type(exc).__name__)
        return None


# ── Context builders ─────────────────────────────────────────────────────────

def _fmt_money(amount: float) -> str:
    return f"{amount:,.2f}"


def _build_report_context(
    data: dict,
    start_date: date | None,
    end_date: date | None,
    period_label: str = "",
) -> str:
    """
    Build a clear context string for Gemini.
    Always shows numeric values (0.00 if zero) and states the period explicitly.
    """
    period = period_label or (
        f"{start_date} to {end_date}" if start_date and end_date
        else "all available data (no date filter applied)"
    )

    revenue = data.get("total_revenue", 0.0)
    expenses = data.get("total_expenses", 0.0)
    net = data.get("net_profit", 0.0)
    has_data = data.get("has_data", False)
    has_error = "error" in data

    if has_error:
        return (
            f"Profit & Loss Report ({period}):\n"
            f"  Status: Could not retrieve data (database error).\n"
            f"  Total Revenue: 0.00\n"
            f"  Total Expenses: 0.00\n"
            f"  Net Profit/Loss: 0.00"
        )

    ctx = [
        f"Profit & Loss Report (period: {period}):",
        f"  Total Revenue: {_fmt_money(revenue)}",
        f"  Total Expenses: {_fmt_money(expenses)}",
        f"  Net Profit/Loss: {_fmt_money(net)}",
    ]

    if not has_data:
        ctx.append(
            f"  Note: No posted journal entries found for this period. "
            f"All values are 0.00 — this is correct, not an error."
        )
    else:
        if data.get("expense_lines"):
            ctx.append("  Top Expenses:")
            for e in sorted(data["expense_lines"], key=lambda x: x["amount"], reverse=True)[:5]:
                ctx.append(f"    - {e['name']}: {_fmt_money(e['amount'])}")
        if data.get("revenue_lines"):
            ctx.append("  Revenue Sources:")
            for r in data["revenue_lines"][:5]:
                ctx.append(f"    - {r['name']}: {_fmt_money(r['amount'])}")

    return "\n".join(ctx)


def _build_audit_context(logs: list[dict]) -> str:
    if not logs:
        return "No audit log entries found."
    lines = [f"Recent Audit Log ({len(logs)} entries):"]
    for log in logs[:8]:
        ts = (log.get("created_at") or "")[:10]
        lines.append(
            f"  - [{ts}] {log.get('actor', 'System')} performed '{log.get('action', '')}' "
            f"on {log.get('entity_type', '')} #{log.get('entity_id', '')} — {log.get('description', '')}"
        )
    return "\n".join(lines)


def _build_journal_context(entries: list[dict], total: int) -> str:
    if not entries:
        return "No journal entries found."
    lines = [f"Journal Entries (total: {total}, showing latest {len(entries)}):"]
    for e in entries:
        lines.append(
            f"  - [{e.get('entry_date')}] {e.get('entry_no')} | {e.get('status')} | "
            f"{e.get('description') or 'No description'} | Debit: {_fmt_money(e.get('total_debit', 0))}"
        )
    return "\n".join(lines)


def _build_user_context(users: list[dict]) -> str:
    if not users:
        return "No company users found."
    active = [u for u in users if u.get("is_active")]
    inactive = [u for u in users if not u.get("is_active")]
    lines = [f"Company Users (total: {len(users)}, active: {len(active)}, inactive: {len(inactive)}):"]
    for u in users[:10]:
        status = "active" if u.get("is_active") else "inactive"
        lines.append(f"  - {u.get('name') or u.get('email') or 'User'} | role: {u.get('role')} | {status}")
    return "\n".join(lines)


# ── Fallback replies (no Gemini) ──────────────────────────────────────────────

def _fallback_report_reply(
    data: dict,
    language: str,
    start_date: date | None,
    end_date: date | None,
    period_label: str = "",
) -> str:
    """
    Deterministic fallback reply for report questions.
    Always shows 0.00 instead of 'no data' — data is always a valid dict now.
    """
    period_str = period_label or (
        f"{start_date} – {end_date}" if start_date and end_date else ""
    )
    period_display = f" ({period_str})" if period_str else ""

    revenue = data.get("total_revenue", 0.0)
    expenses = data.get("total_expenses", 0.0)
    net = data.get("net_profit", 0.0)
    has_data = data.get("has_data", False)

    if language == "ar":
        sign = "ربح" if net >= 0 else "خسارة"
        reply = (
            f"📊 **تقرير الأرباح والخسائر**{period_display}\n"
            f"• إجمالي الإيرادات: **{_fmt_money(revenue)}**\n"
            f"• إجمالي المصاريف: **{_fmt_money(expenses)}**\n"
            f"• صافي {sign}: **{_fmt_money(abs(net))}**"
        )
        if not has_data and period_str:
            reply += (
                f"\n\n💡 لا توجد قيود مرحّلة خلال هذه الفترة. الأرقام أعلاه صحيحة (0.00)."
                f"\nيمكنك سؤالي: 'كم المصاريف إجمالاً؟' لرؤية جميع البيانات."
            )
        return reply

    sign = "Profit" if net >= 0 else "Loss"
    reply = (
        f"📊 **Profit & Loss Report**{period_display}\n"
        f"• Total Revenue: **{_fmt_money(revenue)}**\n"
        f"• Total Expenses: **{_fmt_money(expenses)}**\n"
        f"• Net {sign}: **{_fmt_money(abs(net))}**"
    )
    if not has_data and period_str:
        reply += (
            f"\n\n💡 No posted journal entries found for this period. The 0.00 values above are correct."
            f"\nTry asking: 'What are total expenses overall?' to see all-time data."
        )
    return reply


def _fallback_audit_reply(logs: list[dict], language: str) -> str:
    if not logs:
        return ("لم يتم العثور على سجلات تدقيق." if language == "ar"
                else "No audit log entries found.")
    lines = ["📋 **" + ("آخر نشاطات التدقيق:" if language == "ar" else "Recent Audit Activity:") + "**\n"]
    for log in logs[:5]:
        actor = log.get("actor") or ("النظام" if language == "ar" else "System")
        action = log.get("action", "").replace("_", " ")
        ts = (log.get("created_at") or "")[:10]
        desc = log.get("description") or ""
        lines.append(f"• **{actor}** — {action} — {ts}")
        if desc:
            lines.append(f"  _{desc}_")
    return "\n".join(lines)


def _fallback_journal_reply(entries: list[dict], total: int, language: str) -> str:
    if not entries:
        return ("لا توجد قيود محاسبية حتى الآن." if language == "ar"
                else "No journal entries found.")
    latest = entries[0]
    if language == "ar":
        return (
            f"📒 **إجمالي القيود: {total}**\n\n"
            f"**آخر قيد:**\n"
            f"• الرقم: {latest.get('entry_no')}\n"
            f"• التاريخ: {latest.get('entry_date')}\n"
            f"• الوصف: {latest.get('description') or '—'}\n"
            f"• الحالة: {latest.get('status')}\n"
            f"• الإجمالي المدين: {_fmt_money(latest.get('total_debit', 0))}"
        )
    return (
        f"📒 **Total entries: {total}**\n\n"
        f"**Latest Entry:**\n"
        f"• No.: {latest.get('entry_no')}\n"
        f"• Date: {latest.get('entry_date')}\n"
        f"• Description: {latest.get('description') or '—'}\n"
        f"• Status: {latest.get('status')}\n"
        f"• Total Debit: {_fmt_money(latest.get('total_debit', 0))}"
    )


def _fallback_user_reply(users: list[dict], language: str) -> str:
    if not users:
        return ("لا يوجد مستخدمون." if language == "ar" else "No users found.")
    active = [u for u in users if u.get("is_active")]
    inactive = [u for u in users if not u.get("is_active")]
    if language == "ar":
        lines = [f"👥 **المستخدمون: {len(users)} (نشط: {len(active)} | معطّل: {len(inactive)})**"]
        if inactive:
            lines.append("\n**معطّلون:**")
            for u in inactive[:5]:
                lines.append(f"  - {u.get('name') or u.get('email')} ({u.get('role')})")
        lines.append("\n**نشطون:**")
        for u in active[:5]:
            lines.append(f"  - {u.get('name') or u.get('email')} ({u.get('role')})")
    else:
        lines = [f"👥 **Users: {len(users)} (Active: {len(active)} | Inactive: {len(inactive)})**"]
        if inactive:
            lines.append("\n**Inactive:**")
            for u in inactive[:5]:
                lines.append(f"  - {u.get('name') or u.get('email')} ({u.get('role')})")
        lines.append("\n**Active:**")
        for u in active[:5]:
            lines.append(f"  - {u.get('name') or u.get('email')} ({u.get('role')})")
    return "\n".join(lines)


# ── Action handler (rules engine, never Gemini) ───────────────────────────────

def _handle_action_request(
    db: Session, company_id: int, message: str, language: str,
) -> tuple[str, SuggestedAction | None]:
    accounts_raw = _tool_get_accounts(db, company_id)
    if not accounts_raw:
        msg = ("لا توجد حسابات نشطة." if language == "ar"
               else "No active accounts found in chart of accounts.")
        return msg, None

    from app.modules.accounting.schemas.ai_suggestion_schemas import AccountInfo
    account_infos = [
        AccountInfo(id=a["id"], code=a["code"], name=a["name"],
                    account_type=a["account_type"], is_active=a["is_active"])
        for a in accounts_raw if a["is_active"]
    ]

    result = suggest_journal_entry(description=message, accounts=account_infos, language=language)

    debit_id = result.get("debit_account_id")
    credit_id = result.get("credit_account_id")
    amount = result.get("amount")
    confidence = result.get("confidence", "low")
    explanation = result.get("explanation", "")
    warnings = result.get("warnings", [])
    intent = result.get("detected_intent", "unknown")

    if intent == "unknown" or (not debit_id and not credit_id):
        msg = (
            "لم أتمكن من فهم نوع القيد. يرجى توضيح النية، مثال: 'تم دفع 500 إيجار'."
            if language == "ar"
            else "Couldn't identify the transaction type. Try: 'paid 500 rent' or 'received 1000 from customer'."
        )
        return msg, None

    # ── Refuse explicit non-today dates in user message ────────────────────
    _DATE_PATTERNS = [
        # Arabic explicit date phrases
        r"بتاريخ", r"تاريخ\s+\d", r"أمس", r"البارحة", r"الأمس",
        # English explicit date phrases
        r"\byesterday\b", r"\blast\s+week\b", r"\blast\s+month\b",
        r"\bon\s+\d{4}-\d{2}-\d{2}\b", r"\bdate\s+\d",
        # ISO date in message (not today)
        r"\d{4}-\d{2}-\d{2}",
    ]
    today = get_today_date()
    today_str = today.isoformat()
    for pattern in _DATE_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            matched_text = match.group()
            # Allow if the matched ISO date IS today
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", matched_text) and matched_text == today_str:
                continue
            msg = (
                "يمكن إنشاء القيود عبر مساعد Gemini بتاريخ اليوم فقط."
                if language == "ar"
                else "Gemini Assistant can create journal entries for today's date only."
            )
            return msg, None
    amount_dec = Decimal(str(amount)) if amount else Decimal("0.00")
    accounts_map = {a["id"]: a for a in accounts_raw}
    lines: list[SuggestedJournalLine] = []

    if debit_id and debit_id in accounts_map:
        a = accounts_map[debit_id]
        lines.append(SuggestedJournalLine(
            account_id=a["id"], account_name=a["name"], account_code=a["code"],
            debit=amount_dec, credit=Decimal("0.00"),
        ))
    if credit_id and credit_id in accounts_map:
        a = accounts_map[credit_id]
        lines.append(SuggestedJournalLine(
            account_id=a["id"], account_name=a["name"], account_code=a["code"],
            debit=Decimal("0.00"), credit=amount_dec,
        ))

    if len(lines) < 2:
        msg = (
            f"تم التعرف على النية ({intent}) لكن لا يمكن مطابقة الحسابات. أنشئ القيد يدوياً."
            if language == "ar"
            else f"Recognized intent ({intent}) but couldn't match the required accounts. Please create the entry manually."
        )
        return msg, None

    suggested_action = SuggestedAction(
        type="create_journal_entry_draft",
        requires_confirmation=True,
        payload=SuggestedJournalPayload(
            entry_date=today,
            description=message[:255],
            lines=lines,
            amount=float(amount) if amount else None,
            warnings=warnings,
        ),
    )

    if language == "ar":
        reply = (
            f"✅ النية المُكتشفة: **{intent.replace('_', ' ')}**\n\n"
            f"{explanation}\n\n"
            "📝 **مسودة القيد المقترح:**\n"
        )
        for line in lines:
            if line.debit > 0:
                reply += f"• مدين: **{line.account_name}** ({line.account_code}) — {_fmt_money(float(line.debit))}\n"
            if line.credit > 0:
                reply += f"• دائن: **{line.account_name}** ({line.account_code}) — {_fmt_money(float(line.credit))}\n"
        if warnings:
            reply += "\n⚠️ " + " | ".join(warnings)
        reply += "\n\n🔒 هل تريد إنشاء هذا القيد كمسودة؟"
    else:
        reply = (
            f"✅ Recognized: **{intent.replace('_', ' ').title()}**\n\n"
            f"{explanation}\n\n"
            "📝 **Suggested Draft Entry:**\n"
        )
        for line in lines:
            if line.debit > 0:
                reply += f"• Debit: **{line.account_name}** ({line.account_code}) — {_fmt_money(float(line.debit))}\n"
            if line.credit > 0:
                reply += f"• Credit: **{line.account_name}** ({line.account_code}) — {_fmt_money(float(line.credit))}\n"
        if warnings:
            reply += "\n⚠️ " + " | ".join(warnings)
        reply += "\n\n🔒 Create this as a draft journal entry?"

    return reply, suggested_action


# ── Main dispatcher ───────────────────────────────────────────────────────────

def dispatch_gemini_assistant(
    db: Session,
    company_id: int,
    user_role: str,
    message: str,
    page_context: PageContext,
    language: str,
) -> GeminiAssistantReply:
    """
    Main Gemini Assistant dispatcher.
    1. Checks role permissions
    2. Collects relevant data via internal tools
    3. Tries Gemini for natural language answer (read-only questions)
    4. Falls back to deterministic rules if Gemini unavailable
    5. Uses rules engine for action drafts (always safe, always confirmed)
    """
    intent = _classify_intent(message)

    # ── Access-denied checks ─────────────────────────────────────────────────
    if intent == "audit_question" and user_role not in _CAN_READ_AUDIT_LOGS:
        return GeminiAssistantReply(
            reply=(
                "🔒 ليس لديك صلاحية الوصول إلى سجلات التدقيق."
                if language == "ar"
                else "🔒 You don't have permission to access audit logs."
            ),
            intent="access_denied", confidence="high", data_sources=[],
        )
    if intent == "user_question" and user_role not in _CAN_READ_USERS:
        return GeminiAssistantReply(
            reply=(
                "🔒 ليس لديك صلاحية عرض بيانات المستخدمين."
                if language == "ar"
                else "🔒 You don't have permission to view company user data."
            ),
            intent="access_denied", confidence="high", data_sources=[],
        )
    if intent == "action_request" and user_role not in _CAN_CREATE_DRAFT:
        return GeminiAssistantReply(
            reply=(
                "🔒 ليس لديك صلاحية إنشاء قيود محاسبية. هذه الصلاحية للمحاسب والمدير فقط."
                if language == "ar"
                else "🔒 You don't have permission to create journal entries. Requires admin or accountant role."
            ),
            intent="access_denied", confidence="high", data_sources=[],
        )
    if intent in ("report_question", "balance_question", "journal_question") and user_role not in _CAN_READ_REPORTS:
        return GeminiAssistantReply(
            reply=(
                "🔒 ليس لديك صلاحية الوصول إلى هذه البيانات."
                if language == "ar"
                else "🔒 You don't have permission to access this data."
            ),
            intent="access_denied", confidence="high", data_sources=[],
        )

    # ── Report / P&L question ────────────────────────────────────────────────
    if intent in ("report_question", "balance_question"):
        # 1. Resolve date range: message temporal keywords take priority over page filters
        start_date, end_date, period_label = _extract_date_range(
            message=message,
            page_start=page_context.filters.start_date,
            page_end=page_context.filters.end_date,
        )
        # 2. Fetch data — always returns a dict with numeric values (never {})
        data = _tool_get_profit_loss(db, company_id, start_date, end_date)
        # 3. Build context for Gemini
        context = _build_report_context(data, start_date, end_date, period_label)
        # 4. Try Gemini, fallback to deterministic
        gemini_reply = _call_gemini_for_answer(message, context, language)
        reply = gemini_reply or _fallback_report_reply(
            data, language, start_date, end_date, period_label
        )
        return GeminiAssistantReply(
            reply=reply,
            intent="answer_report_question",
            confidence="high",
            data_sources=["profit_loss_report"],
        )

    # ── Audit question ───────────────────────────────────────────────────────
    if intent == "audit_question":
        action_filter = None
        msg_lower = message.lower()
        if any(w in msg_lower for w in ["role", "permission", "صلاحية", "دور"]):
            action_filter = "update_company_user"
        elif any(w in msg_lower for w in ["posted", "رحّل", "نشر"]):
            action_filter = "post_journal_entry"
        elif any(w in msg_lower for w in ["created", "أنشأ", "create"]):
            action_filter = "create_journal_entry"

        logs = _tool_get_recent_audit_logs(db, company_id, action=action_filter, limit=10)
        context = _build_audit_context(logs)
        gemini_reply = _call_gemini_for_answer(message, context, language)
        reply = gemini_reply or _fallback_audit_reply(logs, language)
        return GeminiAssistantReply(
            reply=reply,
            intent="answer_audit_question",
            confidence="high" if logs else "low",
            data_sources=["audit_logs"],
        )

    # ── Journal question ─────────────────────────────────────────────────────
    if intent == "journal_question":
        entries = _tool_get_recent_journal_entries(db, company_id, limit=5)
        total = count_journal_entries(db=db, company_id=company_id)
        context = _build_journal_context(entries, total)
        gemini_reply = _call_gemini_for_answer(message, context, language)
        reply = gemini_reply or _fallback_journal_reply(entries, total, language)
        return GeminiAssistantReply(
            reply=reply,
            intent="answer_journal_question",
            confidence="high" if entries else "low",
            data_sources=["journal_entries"],
        )

    # ── User question ────────────────────────────────────────────────────────
    if intent == "user_question":
        users = _tool_get_company_users(db, company_id)
        context = _build_user_context(users)
        gemini_reply = _call_gemini_for_answer(message, context, language)
        reply = gemini_reply or _fallback_user_reply(users, language)
        return GeminiAssistantReply(
            reply=reply,
            intent="answer_user_question",
            confidence="high" if users else "low",
            data_sources=["company_users"],
        )

    # ── Action request (rules engine only, never Gemini) ─────────────────────
    if intent == "action_request":
        reply, suggested_action = _handle_action_request(db, company_id, message, language)
        return GeminiAssistantReply(
            reply=reply,
            intent="create_journal_draft" if suggested_action else "clarification",
            confidence="high" if suggested_action else "medium",
            data_sources=["accounts", "rules_engine"],
            suggested_action=suggested_action,
        )

    # ── Unknown / clarification ──────────────────────────────────────────────
    if language == "ar":
        reply = (
            "🤔 لم أفهم سؤالك. يمكنني مساعدتك في:\n"
            "• **التقارير**: 'كم الربح هذا الشهر؟'\n"
            "• **القيود**: 'آخر قيد محاسبي'\n"
            "• **التدقيق**: 'من غير صلاحية المستخدم؟'\n"
            "• **إنشاء قيد**: 'تم دفع 500 إيجار'\n"
            "• **المستخدمون**: 'من المستخدمون النشطون؟'"
        )
    else:
        reply = (
            "🤔 I didn't understand your question. I can help with:\n"
            "• **Reports**: 'What are expenses this month?'\n"
            "• **Journal Entries**: 'Show me the last journal entry'\n"
            "• **Audit Logs**: 'Who changed the user role?'\n"
            "• **Create Entry**: 'Paid 500 rent'\n"
            "• **Users**: 'Who are the active users?'"
        )
    return GeminiAssistantReply(reply=reply, intent="clarification", confidence="low", data_sources=[])
