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
from sqlalchemy import select, func, or_

from app.core.config import settings
from app.core.clock import get_today_date
from app.modules.accounting.schemas.gemini_assistant_schemas import (
    EvidenceEntry,
    GeminiAssistantReply,
    PageContext,
    SuggestedAction,
    SuggestedJournalLine,
    SuggestedJournalPayload,
)
from app.modules.accounting.services.audit_service import list_audit_logs
from app.modules.accounting.services.report_service import (
    get_profit_and_loss,
    get_balance_sheet,
)
from app.modules.accounting.services.account_service import list_accounts
from app.modules.accounting.services.journal_service import (
    list_journal_entries,
    count_journal_entries,
)
from app.modules.accounting.services.company_user_service import list_company_users
from app.modules.accounting.services.ai_suggestion_service import suggest_journal_entry
from app.modules.accounting.models.journal_entry import JournalEntry as JournalEntryModel
from app.modules.accounting.models.journal_line import JournalLine as JournalLineModel
from app.modules.accounting.models.account import Account as AccountModel
from app.modules.accounting.models.audit_log import AuditLog as AuditLogModel

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

    Distinguishes between:
      - Valid empty reports (0.0 values, has_data=False, no error key)
      - Unexpected errors (0.0 values + "error" key for context builder)
    """
    try:
        report = get_profit_and_loss(
            db=db, company_id=company_id,
            start_date=start_date, end_date=end_date,
        )
        return {
            "total_revenue": float(report.total_income),
            "total_expenses": float(report.total_expenses),
            "net_profit": float(report.net_profit),
            "has_data": bool(report.income_lines or report.expense_lines),
            "revenue_lines": [
                {"name": l.account_name, "amount": float(l.amount)}
                for l in report.income_lines
                if float(l.amount) != 0
            ][:10],
            "expense_lines": [
                {"name": l.account_name, "amount": float(l.amount)}
                for l in report.expense_lines
                if float(l.amount) != 0
            ][:10],
        }
    except AttributeError as exc:
        # Schema mismatch = code bug, not a data issue — log loudly
        logger.error(
            "_tool_get_profit_loss schema error (likely code bug): %s", exc,
            exc_info=True,
        )
        return {
            "total_revenue": 0.0,
            "total_expenses": 0.0,
            "net_profit": 0.0,
            "has_data": False,
            "revenue_lines": [],
            "expense_lines": [],
            "error": f"Internal error: {exc}",
        }
    except Exception as exc:
        logger.warning("_tool_get_profit_loss failed: %s", exc)
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


# ── Deep-query tools for explain / trace / who questions ──────────────────────


def _tool_get_journal_entries_with_lines(
    db: Session, company_id: int, status: str = "posted", limit: int = 50,
) -> list[dict]:
    """Get journal entries with full line-level detail (accounts, amounts)."""
    try:
        entries = list_journal_entries(
            db=db, company_id=company_id, status=status, limit=limit,
        )
        # Build account name lookup
        accounts = {a.id: a for a in db.scalars(
            select(AccountModel).where(AccountModel.company_id == company_id)
        ).all()}

        result = []
        for e in entries:
            lines = []
            for line in e.lines:
                acc = accounts.get(line.account_id)
                lines.append({
                    "account_id": line.account_id,
                    "account_name": acc.name if acc else f"Account #{line.account_id}",
                    "account_code": acc.code if acc else "?",
                    "account_type": acc.account_type if acc else "unknown",
                    "debit": float(line.debit),
                    "credit": float(line.credit),
                })
            result.append({
                "id": e.id,
                "entry_no": e.entry_no,
                "entry_date": str(e.entry_date),
                "description": e.description,
                "status": e.status,
                "source_type": e.source_type,
                "total_debit": float(sum(l.debit for l in e.lines)),
                "lines": lines,
            })
        return result
    except Exception as exc:
        logger.warning("_tool_get_journal_entries_with_lines failed: %s", exc)
        return []


def _tool_trace_amount(
    db: Session, company_id: int, amount: float, account_hint: str | None = None,
) -> list[dict]:
    """Find journal entries containing a line matching the given amount (±0.01)."""
    try:
        target = Decimal(str(amount))
        tolerance = Decimal("0.01")

        stmt = (
            select(JournalEntryModel)
            .join(JournalLineModel, JournalLineModel.journal_entry_id == JournalEntryModel.id)
            .where(
                JournalEntryModel.company_id == company_id,
                or_(
                    func.abs(JournalLineModel.debit - target) <= tolerance,
                    func.abs(JournalLineModel.credit - target) <= tolerance,
                ),
            )
            .distinct()
            .order_by(JournalEntryModel.entry_date.desc())
            .limit(10)
        )
        entries = list(db.scalars(stmt).all())

        # Account lookup
        accounts = {a.id: a for a in db.scalars(
            select(AccountModel).where(AccountModel.company_id == company_id)
        ).all()}

        result = []
        for e in entries:
            # Reload lines
            db.refresh(e, ["lines"])
            matching_lines = [
                l for l in e.lines
                if abs(float(l.debit) - amount) < 0.02 or abs(float(l.credit) - amount) < 0.02
            ]
            debit_accounts = []
            credit_accounts = []
            for line in e.lines:
                acc = accounts.get(line.account_id)
                acc_name = acc.name if acc else f"#{line.account_id}"
                if float(line.debit) > 0:
                    debit_accounts.append(acc_name)
                if float(line.credit) > 0:
                    credit_accounts.append(acc_name)

            # Try to find actor from audit log
            actor = _tool_get_entry_actor(db, company_id, e.id)

            entry_dict = {
                "entry_no": e.entry_no,
                "entry_date": str(e.entry_date),
                "description": e.description,
                "status": e.status,
                "source_type": e.source_type,
                "amount": amount,
                "debit_accounts": debit_accounts,
                "credit_accounts": credit_accounts,
                "created_by": actor.get("created_by"),
                "posted_by": actor.get("posted_by"),
            }

            # Filter by account hint if provided
            if account_hint:
                hint_lower = account_hint.lower()
                all_acc_names = [n.lower() for n in debit_accounts + credit_accounts]
                if not any(hint_lower in n for n in all_acc_names):
                    continue

            result.append(entry_dict)
        return result
    except Exception as exc:
        logger.warning("_tool_trace_amount failed: %s", exc)
        return []


def _tool_get_balance_sheet_data(db: Session, company_id: int) -> dict:
    """Get balance sheet totals and contributing account lines."""
    try:
        bs = get_balance_sheet(db=db, company_id=company_id)
        return {
            "total_assets": float(bs.total_assets),
            "total_liabilities": float(bs.total_liabilities),
            "total_equity": float(bs.total_equity),
            "current_year_earnings": float(bs.current_year_earnings),
            "total_liabilities_and_equity": float(bs.total_liabilities_and_equity),
            "is_balanced": bs.is_balanced,
            "asset_lines": [
                {"name": l.account_name, "code": l.account_code, "amount": float(l.amount)}
                for l in bs.asset_lines if float(l.amount) != 0
            ],
            "liability_lines": [
                {"name": l.account_name, "code": l.account_code, "amount": float(l.amount)}
                for l in bs.liability_lines if float(l.amount) != 0
            ],
            "equity_lines": [
                {"name": l.account_name, "code": l.account_code, "amount": float(l.amount)}
                for l in bs.equity_lines if float(l.amount) != 0
            ],
        }
    except Exception as exc:
        logger.warning("_tool_get_balance_sheet_data failed: %s", exc)
        return {"error": str(exc)}


def _tool_get_account_entries(
    db: Session, company_id: int, account_name_hint: str, limit: int = 10,
) -> list[dict]:
    """Get posted journal entries affecting a specific account (matched by name substring)."""
    try:
        # Find matching account(s)
        accs = db.scalars(
            select(AccountModel).where(
                AccountModel.company_id == company_id,
                AccountModel.name.ilike(f"%{account_name_hint}%"),
            )
        ).all()
        if not accs:
            return []

        acc_ids = [a.id for a in accs]
        acc_map = {a.id: a for a in accs}

        stmt = (
            select(JournalEntryModel)
            .join(JournalLineModel, JournalLineModel.journal_entry_id == JournalEntryModel.id)
            .where(
                JournalEntryModel.company_id == company_id,
                JournalEntryModel.status == "posted",
                JournalLineModel.account_id.in_(acc_ids),
            )
            .distinct()
            .order_by(JournalEntryModel.entry_date.desc())
            .limit(limit)
        )
        entries = list(db.scalars(stmt).all())

        # Build all-account lookup for line details
        all_accounts = {a.id: a for a in db.scalars(
            select(AccountModel).where(AccountModel.company_id == company_id)
        ).all()}

        result = []
        for e in entries:
            db.refresh(e, ["lines"])
            lines = []
            for line in e.lines:
                acc = all_accounts.get(line.account_id)
                lines.append({
                    "account_name": acc.name if acc else f"#{line.account_id}",
                    "account_type": acc.account_type if acc else "unknown",
                    "debit": float(line.debit),
                    "credit": float(line.credit),
                })
            result.append({
                "entry_no": e.entry_no,
                "entry_date": str(e.entry_date),
                "description": e.description,
                "status": e.status,
                "total_amount": float(sum(l.debit for l in e.lines)),
                "lines": lines,
            })
        return result
    except Exception as exc:
        logger.warning("_tool_get_account_entries failed: %s", exc)
        return []


def _tool_get_entry_actor(
    db: Session, company_id: int, entry_id: int,
) -> dict:
    """Get who created/posted a specific journal entry from audit logs."""
    result = {"created_by": None, "posted_by": None, "reviewed_by": None}
    try:
        logs = list_audit_logs(
            db=db, company_id=company_id,
            entity_type="journal_entry", entity_id=entry_id,
            limit=20,
        )
        for log in logs:
            actor = log.actor_name or log.actor_email or log.actor
            if log.action in ("create_journal_entry", "create_journal_draft_via_gemini") and not result["created_by"]:
                result["created_by"] = actor
            elif log.action == "post_journal_entry" and not result["posted_by"]:
                result["posted_by"] = actor
            elif log.action == "review_journal_entry" and not result["reviewed_by"]:
                result["reviewed_by"] = actor
    except Exception as exc:
        logger.warning("_tool_get_entry_actor failed: %s", exc)
    return result


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

    # ── Explain questions (how/why a figure was formed) ────────────────────
    explain_arabic = any(phrase in text for phrase in [
        "كيف صار", "كيف صارت", "كيف وصل", "كيف وصلت",
        "ليش", "لماذا", "من وين جا", "من وين جاء", "من وين جت",
        "وريني تفاصيل", "اشرح", "فسر", "تفاصيل",
        "كيف تحسب", "كيف تكون", "كيف تكونت",
        "ايش القيود", "ايش اللي كون", "ايش اللي صنع",
        "ارباحي من وين", "من وين الربح", "من وين الدخل",
        "كيف دخلنا", "ايش دخلنا",
    ])
    explain_english = bool(re.search(
        r"\b(how did|why is|why are|explain|show me what makes|what makes up|"
        r"break ?down|composed of|formed|trace profit|explain the)\b",
        text, re.IGNORECASE,
    ))
    if explain_arabic or explain_english:
        return "explain_question"

    # ── Trace questions (who entered/where did amount go) ─────────────────
    # Extract amount to detect trace intent
    _has_amount = bool(re.search(r"\d[\d,]*\.?\d*", text))
    trace_arabic = _has_amount and any(phrase in text for phrase in [
        "من أدخل", "من سجل", "من رفع", "من دخل", "من عمل",
        "مين دخل", "مين سجل", "مين أدخل",
        "ايش هذا", "ايش هذي", "وين راح", "وين راحت",
        "من اللي أضاف", "من اللي دخل", "من اللي سجل",
    ])
    trace_english = _has_amount and bool(re.search(
        r"\b(who entered|who recorded|who created|where did|what is this)\b",
        text, re.IGNORECASE,
    ))
    # Also catch "وين راحت 500" / "وين راح 500" without requiring other phrases
    trace_where = bool(re.search(r"(وين\s*راح|وين\s*راحت)", text))
    if trace_arabic or trace_english or trace_where:
        return "trace_question"

    # ── Who-did-action questions (audit-actor focused) ────────────────────
    who_action_arabic = any(phrase in text for phrase in [
        "من رحّل", "من رحل", "من راجع", "من أنشأ", "من انشأ",
        "من آخر واحد", "من اخر واحد",
        "من غير الصلاحية", "من حذف", "من عدل",
        "مين رحل", "مين راجع", "مين أنشأ",
        "من اللي رحل", "من الذي رحل", "من الذي أنشأ",
        "من اللي أنشأ", "من الذي أنشأ قيد",
    ])
    who_action_english = bool(re.search(
        r"\b(who posted|who reviewed|who created the|who made the|"
        r"who changed|who deleted|who modified|last person)\b",
        text, re.IGNORECASE,
    ))
    if who_action_arabic or who_action_english:
        return "who_action_question"

    # Report / financial questions
    if any(t in text_lower for t in [
        "profit", "loss", "revenue", "income", "expense", "expenses",
        "ربح", "خسارة", "إيراد", "ايراد", "مصروف", "مصاريف",
        "how much", "كم", "total", "إجمالي", "اجمالي",
        "كم دفعنا", "كم خرجنا", "كم دخلنا",
    ]):
        return "report_question"

    # Balance questions
    if any(t in text_lower for t in [
        "balance", "trial balance", "balance sheet",
        "رصيد", "ميزانية", "ميزان المراجعة",
        "أصول", "اصول", "assets",
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

    # If the data fetch failed, show an error instead of fake zeros
    if "error" in data:
        if language == "ar":
            return (
                f"⚠️ تعذّر استرجاع بيانات الأرباح والخسائر{period_display}. "
                f"يرجى المحاولة مرة أخرى أو مراجعة صفحة التقارير مباشرة."
            )
        return (
            f"⚠️ Could not retrieve Profit & Loss data{period_display}. "
            f"Please try again or check the Reports page directly."
        )

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


# ── Helpers for new intents ───────────────────────────────────────────────────


def _extract_amount_from_message(message: str) -> float | None:
    """Extract a numeric amount from the user's message."""
    # Match numbers like 1,500.00 or 1500 or 500
    matches = re.findall(r'[\d,]+\.?\d*', message)
    for m in matches:
        try:
            val = float(m.replace(',', ''))
            if val > 0:
                return val
        except ValueError:
            continue
    return None


def _extract_account_hint(message: str) -> str | None:
    """Extract an account name hint from the message."""
    account_keywords = {
        "إيجار": "rent", "ايجار": "rent", "rent": "rent",
        "مبيعات": "sales", "sales": "sales", "revenue": "revenue",
        "بنك": "bank", "bank": "bank",
        "إيراد": "revenue", "ايراد": "revenue", "income": "income",
        "مصروف": "expense", "expense": "expense",
    }
    text_lower = message.lower()
    for ar_word, en_word in account_keywords.items():
        if ar_word in text_lower or ar_word in message:
            return en_word
    return None


# ── Context builders for new intents ──────────────────────────────────────────


def _build_explain_context(
    pl_data: dict,
    entries: list[dict],
    bs_data: dict | None = None,
) -> str:
    """Build context for explain questions — includes P&L + journal entry evidence."""
    ctx = []

    # P&L summary
    revenue = pl_data.get("total_revenue", 0.0)
    expenses = pl_data.get("total_expenses", 0.0)
    net = pl_data.get("net_profit", 0.0)
    ctx.append("=== Profit & Loss Summary ===")
    ctx.append(f"Total Revenue: {_fmt_money(revenue)}")
    ctx.append(f"Total Expenses: {_fmt_money(expenses)}")
    ctx.append(f"Net Profit/Loss: {_fmt_money(net)}")

    # Revenue breakdown by account
    if pl_data.get("revenue_lines"):
        ctx.append("\nRevenue Sources:")
        for r in pl_data["revenue_lines"]:
            ctx.append(f"  - {r['name']}: {_fmt_money(r['amount'])}")

    # Expense breakdown by account
    if pl_data.get("expense_lines"):
        ctx.append("\nExpense Sources:")
        for e in pl_data["expense_lines"]:
            ctx.append(f"  - {e['name']}: {_fmt_money(e['amount'])}")

    # Contributing journal entries
    if entries:
        ctx.append(f"\n=== Contributing Posted Journal Entries ({len(entries)} entries) ===")
        for e in entries[:15]:
            lines_desc = []
            for line in e.get("lines", []):
                if line["debit"] > 0:
                    lines_desc.append(f"Dr {line['account_name']} {_fmt_money(line['debit'])}")
                if line["credit"] > 0:
                    lines_desc.append(f"Cr {line['account_name']} {_fmt_money(line['credit'])}")
            ctx.append(
                f"  Entry {e['entry_no']} ({e['entry_date']}) — {e.get('description') or 'No description'} — "
                f"Status: {e['status']} — {' | '.join(lines_desc)}"
            )

    # Balance sheet if relevant
    if bs_data and "error" not in bs_data:
        ctx.append(f"\n=== Balance Sheet ===")
        ctx.append(f"Total Assets: {_fmt_money(bs_data.get('total_assets', 0))}")
        ctx.append(f"Total Liabilities: {_fmt_money(bs_data.get('total_liabilities', 0))}")
        ctx.append(f"Total Equity: {_fmt_money(bs_data.get('total_equity', 0))}")
        ctx.append(f"Current Year Earnings: {_fmt_money(bs_data.get('current_year_earnings', 0))}")
        if bs_data.get("asset_lines"):
            ctx.append("Asset Accounts:")
            for a in bs_data["asset_lines"]:
                ctx.append(f"  - {a['name']}: {_fmt_money(a['amount'])}")

    return "\n".join(ctx)


def _build_trace_context(matches: list[dict]) -> str:
    """Build context for trace questions — matching entries + actor info."""
    if not matches:
        return "No journal entries found matching the given amount."

    ctx = [f"=== Matching Journal Entries ({len(matches)} found) ==="]
    for m in matches:
        ctx.append(
            f"Entry {m['entry_no']} ({m['entry_date']}) — Status: {m['status']} — "
            f"Amount: {_fmt_money(m['amount'])} — "
            f"Dr: {', '.join(m.get('debit_accounts', []))} — "
            f"Cr: {', '.join(m.get('credit_accounts', []))} — "
            f"Description: {m.get('description') or 'None'} — "
            f"Created by: {m.get('created_by') or 'Unknown'} — "
            f"Posted by: {m.get('posted_by') or 'N/A'}"
        )
    return "\n".join(ctx)


def _build_who_action_context(logs: list[dict]) -> str:
    """Build context for who-action questions — audit logs with actor details."""
    if not logs:
        return "No audit logs found for the requested action."

    ctx = [f"=== Audit Logs ({len(logs)} entries) ==="]
    for log in logs[:10]:
        ctx.append(
            f"[{(log.get('created_at') or '')[:19]}] "
            f"Actor: {log.get('actor') or 'System'} — "
            f"Action: {log.get('action', '')} — "
            f"Entity: {log.get('entity_type', '')} #{log.get('entity_id', '')} — "
            f"Description: {log.get('description') or 'None'}"
        )
    return "\n".join(ctx)


# ── Fallback replies for new intents ──────────────────────────────────────────


def _fallback_explain_reply(
    pl_data: dict,
    entries: list[dict],
    language: str,
    bs_data: dict | None = None,
) -> str:
    """Deterministic explanation of how figures were formed."""
    revenue = pl_data.get("total_revenue", 0.0)
    expenses = pl_data.get("total_expenses", 0.0)
    net = pl_data.get("net_profit", 0.0)

    if language == "ar":
        parts = []

        # Revenue explanation
        if revenue > 0:
            rev_lines = pl_data.get("revenue_lines", [])
            if rev_lines:
                rev_desc = "، ".join(
                    f"{r['name']} بقيمة {_fmt_money(r['amount'])}" for r in rev_lines
                )
                parts.append(f"📊 **الإيرادات {_fmt_money(revenue)}** تتكون من: {rev_desc}.")
            else:
                parts.append(f"📊 إجمالي الإيرادات: **{_fmt_money(revenue)}**")

        # Expense explanation
        if expenses > 0:
            exp_lines = pl_data.get("expense_lines", [])
            if exp_lines:
                exp_desc = "، ".join(
                    f"{e['name']} بقيمة {_fmt_money(e['amount'])}" for e in exp_lines
                )
                parts.append(f"💰 **المصاريف {_fmt_money(expenses)}** تتكون من: {exp_desc}.")
            else:
                parts.append(f"💰 إجمالي المصاريف: **{_fmt_money(expenses)}**")

        # Net profit explanation
        sign = "ربح" if net >= 0 else "خسارة"
        parts.append(
            f"📈 **صافي {sign}: {_fmt_money(abs(net))}** "
            f"= الإيرادات {_fmt_money(revenue)} - المصاريف {_fmt_money(expenses)}"
        )

        # Contributing entries
        if entries:
            parts.append(f"\n📝 **القيود المؤثرة ({len(entries)} قيد):**")
            for e in entries[:10]:
                debit_parts = []
                credit_parts = []
                for line in e.get("lines", []):
                    if line["debit"] > 0:
                        debit_parts.append(f"{line['account_name']} {_fmt_money(line['debit'])}")
                    if line["credit"] > 0:
                        credit_parts.append(f"{line['account_name']} {_fmt_money(line['credit'])}")
                parts.append(
                    f"• **{e['entry_no']}** ({e['entry_date']}) — "
                    f"مدين: {', '.join(debit_parts)} | دائن: {', '.join(credit_parts)}"
                )

        # Balance sheet if relevant
        if bs_data and "error" not in bs_data:
            ta = bs_data.get("total_assets", 0)
            tl = bs_data.get("total_liabilities", 0)
            te = bs_data.get("total_equity", 0)
            cye = bs_data.get("current_year_earnings", 0)
            parts.append(
                f"\n🏦 **الميزانية:** الأصول {_fmt_money(ta)} = "
                f"الالتزامات {_fmt_money(tl)} + حقوق الملكية {_fmt_money(te)} + "
                f"أرباح العام {_fmt_money(cye)}"
            )

        return "\n".join(parts)

    # English
    parts = []
    if revenue > 0:
        rev_lines = pl_data.get("revenue_lines", [])
        if rev_lines:
            rev_desc = ", ".join(f"{r['name']} ({_fmt_money(r['amount'])})" for r in rev_lines)
            parts.append(f"📊 **Revenue {_fmt_money(revenue)}** is composed of: {rev_desc}.")
        else:
            parts.append(f"📊 Total Revenue: **{_fmt_money(revenue)}**")

    if expenses > 0:
        exp_lines = pl_data.get("expense_lines", [])
        if exp_lines:
            exp_desc = ", ".join(f"{e['name']} ({_fmt_money(e['amount'])})" for e in exp_lines)
            parts.append(f"💰 **Expenses {_fmt_money(expenses)}** are composed of: {exp_desc}.")
        else:
            parts.append(f"💰 Total Expenses: **{_fmt_money(expenses)}**")

    sign = "Profit" if net >= 0 else "Loss"
    parts.append(
        f"📈 **Net {sign}: {_fmt_money(abs(net))}** "
        f"= Revenue {_fmt_money(revenue)} - Expenses {_fmt_money(expenses)}"
    )

    if entries:
        parts.append(f"\n📝 **Contributing Entries ({len(entries)}):**")
        for e in entries[:10]:
            debit_parts = []
            credit_parts = []
            for line in e.get("lines", []):
                if line["debit"] > 0:
                    debit_parts.append(f"{line['account_name']} {_fmt_money(line['debit'])}")
                if line["credit"] > 0:
                    credit_parts.append(f"{line['account_name']} {_fmt_money(line['credit'])}")
            parts.append(
                f"• **{e['entry_no']}** ({e['entry_date']}) — "
                f"Dr: {', '.join(debit_parts)} | Cr: {', '.join(credit_parts)}"
            )

    return "\n".join(parts)


def _fallback_trace_reply(matches: list[dict], amount: float, language: str) -> str:
    """Deterministic reply for amount tracing."""
    if not matches:
        if language == "ar":
            return f"🔍 لم أجد قيدًا مطابقًا لمبلغ **{_fmt_money(amount)}** في الشركة الحالية."
        return f"🔍 I could not find a matching entry for **{_fmt_money(amount)}** in the selected company."

    if len(matches) == 1:
        m = matches[0]
        if language == "ar":
            actor = m.get("created_by") or "غير معروف"
            posted_by = m.get("posted_by")
            reply = (
                f"🔍 تم إدخال **{_fmt_money(amount)}** بواسطة **{actor}** "
                f"في القيد رقم **{m['entry_no']}** بتاريخ {m['entry_date']}.\n"
                f"• الحالة: {m['status']}\n"
                f"• مدين: {', '.join(m.get('debit_accounts', []))}\n"
                f"• دائن: {', '.join(m.get('credit_accounts', []))}"
            )
            if posted_by:
                reply += f"\n• رحّله: **{posted_by}**"
            if m.get("description"):
                reply += f"\n• الوصف: {m['description']}"
            return reply

        actor = m.get("created_by") or "Unknown"
        posted_by = m.get("posted_by")
        reply = (
            f"🔍 **{_fmt_money(amount)}** was entered by **{actor}** "
            f"in entry **{m['entry_no']}** on {m['entry_date']}.\n"
            f"• Status: {m['status']}\n"
            f"• Debit: {', '.join(m.get('debit_accounts', []))}\n"
            f"• Credit: {', '.join(m.get('credit_accounts', []))}"
        )
        if posted_by:
            reply += f"\n• Posted by: **{posted_by}**"
        if m.get("description"):
            reply += f"\n• Description: {m['description']}"
        return reply

    # Multiple matches
    if language == "ar":
        lines = [f"🔍 وجدت **{len(matches)}** عمليات بقيمة **{_fmt_money(amount)}**:\n"]
        for i, m in enumerate(matches[:5], 1):
            actor = m.get("created_by") or "غير معروف"
            lines.append(
                f"{i}. **{m['entry_no']}** ({m['entry_date']}) — "
                f"{', '.join(m.get('credit_accounts', []))} — "
                f"بواسطة {actor} — الحالة: {m['status']}"
            )
        lines.append("\nأي عملية تقصد؟")
        return "\n".join(lines)

    lines = [f"🔍 Found **{len(matches)}** entries with amount **{_fmt_money(amount)}**:\n"]
    for i, m in enumerate(matches[:5], 1):
        actor = m.get("created_by") or "Unknown"
        lines.append(
            f"{i}. **{m['entry_no']}** ({m['entry_date']}) — "
            f"{', '.join(m.get('credit_accounts', []))} — "
            f"by {actor} — Status: {m['status']}"
        )
    lines.append("\nWhich one do you mean?")
    return "\n".join(lines)


def _fallback_who_action_reply(logs: list[dict], language: str, action_desc: str = "") -> str:
    """Deterministic reply for who-did-action questions."""
    if not logs:
        if language == "ar":
            return f"🔍 لم أجد سجل تدقيق يطابق '{action_desc}'."
        return f"🔍 No audit log found matching '{action_desc}'."

    latest = logs[0]
    actor = latest.get("actor") or ("النظام" if language == "ar" else "System")
    action = latest.get("action", "").replace("_", " ")
    ts = (latest.get("created_at") or "")[:19]
    desc = latest.get("description") or ""

    if language == "ar":
        reply = (
            f"👤 **{actor}** قام بعملية **{action}**"
            f" بتاريخ {ts}."
        )
        if desc:
            reply += f"\n• الوصف: {desc}"
        if len(logs) > 1:
            reply += f"\n\n📋 **آخر {min(len(logs), 5)} عمليات:**"
            for log in logs[:5]:
                log_actor = log.get("actor") or "النظام"
                log_ts = (log.get("created_at") or "")[:19]
                reply += f"\n• {log_actor} — {log.get('action', '').replace('_', ' ')} — {log_ts}"
        return reply

    reply = (
        f"👤 **{actor}** performed **{action}**"
        f" at {ts}."
    )
    if desc:
        reply += f"\n• Description: {desc}"
    if len(logs) > 1:
        reply += f"\n\n📋 **Last {min(len(logs), 5)} actions:**"
        for log in logs[:5]:
            log_actor = log.get("actor") or "System"
            log_ts = (log.get("created_at") or "")[:19]
            reply += f"\n• {log_actor} — {log.get('action', '').replace('_', ' ')} — {log_ts}"
    return reply


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
    if intent in ("report_question", "balance_question", "journal_question", "explain_question") and user_role not in _CAN_READ_REPORTS:
        return GeminiAssistantReply(
            reply=(
                "🔒 ليس لديك صلاحية الوصول إلى هذه البيانات."
                if language == "ar"
                else "🔒 You don't have permission to access this data."
            ),
            intent="access_denied", confidence="high", data_sources=[],
        )
    if intent == "trace_question" and user_role not in _CAN_READ_REPORTS:
        return GeminiAssistantReply(
            reply=(
                "🔒 ليس لديك صلاحية الوصول إلى هذه البيانات."
                if language == "ar"
                else "🔒 You don't have permission to access this data."
            ),
            intent="access_denied", confidence="high", data_sources=[],
        )
    if intent == "who_action_question" and user_role not in _CAN_READ_AUDIT_LOGS:
        return GeminiAssistantReply(
            reply=(
                "🔒 ليس لديك صلاحية الوصول إلى سجلات التدقيق."
                if language == "ar"
                else "🔒 You don't have permission to access audit logs."
            ),
            intent="access_denied", confidence="high", data_sources=[],
        )

    # ── Explain question (how/why a figure was formed) ────────────────────────
    if intent == "explain_question":
        # Fetch P&L data
        start_date, end_date, period_label = _extract_date_range(
            message=message,
            page_start=page_context.filters.start_date,
            page_end=page_context.filters.end_date,
        )
        pl_data = _tool_get_profit_loss(db, company_id, start_date, end_date)
        # Fetch journal entries with full line details
        entries = _tool_get_journal_entries_with_lines(db, company_id, status="posted")
        # Check if balance sheet is relevant
        msg_lower = message.lower()
        bs_data = None
        if any(w in msg_lower for w in [
            "أصول", "اصول", "assets", "ميزانية", "balance",
            "بنك", "bank", "رصيد",
        ]):
            bs_data = _tool_get_balance_sheet_data(db, company_id)

        # Build evidence list
        evidence = [
            EvidenceEntry(
                entry_no=e["entry_no"],
                date=e["entry_date"],
                amount=e.get("total_debit"),
                debit_account=", ".join(
                    l["account_name"] for l in e.get("lines", []) if l["debit"] > 0
                ),
                credit_account=", ".join(
                    l["account_name"] for l in e.get("lines", []) if l["credit"] > 0
                ),
                status=e["status"],
                description=e.get("description"),
            )
            for e in entries[:10]
        ]

        context = _build_explain_context(pl_data, entries, bs_data)
        gemini_reply = _call_gemini_for_answer(message, context, language)
        reply = gemini_reply or _fallback_explain_reply(pl_data, entries, language, bs_data)

        data_sources = ["profit_loss_report", "journal_entries"]
        if bs_data:
            data_sources.append("balance_sheet")

        return GeminiAssistantReply(
            reply=reply,
            intent="answer_explain_question",
            confidence="high" if entries else "medium",
            data_sources=data_sources,
            evidence=evidence,
        )

    # ── Trace question (who entered / where did amount go) ────────────────────
    if intent == "trace_question":
        amount = _extract_amount_from_message(message)
        account_hint = _extract_account_hint(message)

        if amount is None:
            if language == "ar":
                reply = "🤔 لم أتمكن من تحديد المبلغ. حدد المبلغ المطلوب تتبعه، مثل: 'من أدخل 1000؟'"
            else:
                reply = "🤔 I couldn't identify the amount. Please specify, e.g. 'Who entered 1000?'"
            return GeminiAssistantReply(
                reply=reply,
                intent="clarification",
                confidence="low",
                data_sources=[],
            )

        matches = _tool_trace_amount(db, company_id, amount, account_hint)
        evidence = [
            EvidenceEntry(
                entry_no=m["entry_no"],
                date=m["entry_date"],
                amount=m["amount"],
                debit_account=", ".join(m.get("debit_accounts", [])),
                credit_account=", ".join(m.get("credit_accounts", [])),
                status=m["status"],
                actor_name=m.get("created_by"),
                description=m.get("description"),
            )
            for m in matches
        ]

        context = _build_trace_context(matches)
        gemini_reply = _call_gemini_for_answer(message, context, language)
        reply = gemini_reply or _fallback_trace_reply(matches, amount, language)

        return GeminiAssistantReply(
            reply=reply,
            intent="answer_trace_question",
            confidence="high" if matches else "medium",
            data_sources=["journal_entries", "audit_logs"],
            evidence=evidence,
        )

    # ── Who-action question (who posted / reviewed / created) ─────────────────
    if intent == "who_action_question":
        # Determine action filter from message
        action_filter = None
        msg_lower = message.lower()
        if any(w in msg_lower for w in ["رحّل", "رحل", "posted", "نشر"]):
            action_filter = "post_journal_entry"
        elif any(w in msg_lower for w in ["راجع", "reviewed", "review"]):
            action_filter = "review_journal_entry"
        elif any(w in msg_lower for w in ["أنشأ", "انشأ", "created", "create", "سجل"]):
            action_filter = "create_journal_entry"
        elif any(w in msg_lower for w in ["غير", "عدل", "changed", "modified"]):
            action_filter = "update_company_user"
        elif any(w in msg_lower for w in ["حذف", "deleted", "removed"]):
            action_filter = "remove_company_access"

        action_desc = action_filter or "recent actions"
        logs = _tool_get_recent_audit_logs(db, company_id, action=action_filter, limit=10)
        context = _build_who_action_context(logs)
        gemini_reply = _call_gemini_for_answer(message, context, language)
        reply = gemini_reply or _fallback_who_action_reply(logs, language, action_desc)

        return GeminiAssistantReply(
            reply=reply,
            intent="answer_who_action_question",
            confidence="high" if logs else "low",
            data_sources=["audit_logs"],
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
            "• **شرح الأرقام**: 'كيف صارت الإيرادات 2000؟'\n"
            "• **تتبع مبلغ**: 'من أدخل 1000؟'\n"
            "• **القيود**: 'آخر قيد محاسبي'\n"
            "• **التدقيق**: 'من رحّل القيد؟'\n"
            "• **إنشاء قيد**: 'تم دفع 500 إيجار'\n"
            "• **المستخدمون**: 'من المستخدمون النشطون؟'"
        )
    else:
        reply = (
            "🤔 I didn't understand your question. I can help with:\n"
            "• **Reports**: 'What are expenses this month?'\n"
            "• **Explain Figures**: 'How did revenue become 2000?'\n"
            "• **Trace Amounts**: 'Who entered 1000?'\n"
            "• **Journal Entries**: 'Show me the last journal entry'\n"
            "• **Audit**: 'Who posted the last entry?'\n"
            "• **Create Entry**: 'Paid 500 rent'\n"
            "• **Users**: 'Who are the active users?'"
        )
    return GeminiAssistantReply(reply=reply, intent="clarification", confidence="low", data_sources=[])
