"""
AI routes:
  POST /ai/journal-suggestions          — existing journal assistant (unchanged)
  GET  /ai/status                       — existing AI provider status (unchanged)
  POST /ai/gemini-assistant             — Gemini Assistant chat
  POST /ai/gemini-assistant/confirm-action — confirmed action execution
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.ai_suggestion_schemas import (
    AiStatusResponse,
    JournalSuggestionRequest,
    JournalSuggestionResponse,
)
from app.modules.accounting.schemas.gemini_assistant_schemas import (
    ConfirmActionReply,
    ConfirmActionRequest,
    GeminiAssistantReply,
    GeminiAssistantRequest,
)
from app.modules.accounting.services.ai_provider_factory import (
    get_journal_suggestion_provider,
    get_provider_status,
)
from app.modules.accounting.services.audit_service import create_audit_log
from app.modules.accounting.services.gemini_assistant_service import dispatch_gemini_assistant
from app.modules.accounting.services.journal_service import (
    create_journal_entry,
    find_fiscal_period_for_date,
    find_fiscal_year_for_date,
    get_account,
    get_company_or_none,
    get_journal_entry_by_no,
)
from app.modules.accounting.schemas.journal import (
    JournalEntryCreate,
    JournalLineCreate,
)


router = APIRouter(
    prefix="/ai",
    tags=["AI Assistant"],
)


# ── Existing endpoints (unchanged) ────────────────────────────────────────────

@router.post(
    "/journal-suggestions",
    response_model=JournalSuggestionResponse,
    status_code=status.HTTP_200_OK,
)
def suggest_journal_entry_endpoint(
    payload: JournalSuggestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
    )

    provider = get_journal_suggestion_provider()

    result = provider.suggest_journal_entry(
        description=payload.description,
        accounts=payload.accounts,
        language=payload.language,
    )

    return JournalSuggestionResponse(**result)


@router.get(
    "/status",
    response_model=AiStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_ai_status_endpoint(
    current_user: User = Depends(get_current_user),
):
    status_data = get_provider_status()
    return AiStatusResponse(**status_data)


# ── Gemini Assistant ──────────────────────────────────────────────────────

@router.post(
    "/gemini-assistant",
    response_model=GeminiAssistantReply,
    status_code=status.HTTP_200_OK,
)
def gemini_assistant_chat_endpoint(
    payload: GeminiAssistantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Gemini Assistant endpoint.
    - Requires authentication and company membership (any role).
    - Dispatches to Gemini (if configured) or rules fallback.
    - Never executes mutations — only returns SuggestedAction for confirmation.
    - Never exposes secrets, tokens, or cross-company data.
    """
    company_user = ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
    )

    user_role = company_user.role if company_user else "viewer"

    return dispatch_gemini_assistant(
        db=db,
        company_id=payload.company_id,
        user_role=user_role,
        message=payload.message,
        page_context=payload.page_context,
        language=payload.language,
    )


@router.post(
    "/gemini-assistant/confirm-action",
    response_model=ConfirmActionReply,
    status_code=status.HTTP_200_OK,  # 200 for both success and structured failures
)
def gemini_assistant_confirm_action_endpoint(
    payload: ConfirmActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute a previously suggested Gemini Assistant action after explicit user confirmation.
    Currently supports: create_journal_entry_draft

    Returns HTTP 200 for both success and structured validation errors.
    On failure, response contains: success=False, error_code, message.
    On success, response contains: success=True, entity_id, data.

    Full re-validation:
      - Auth + company access + role (admin/accountant only)
      - Balanced entry
      - Active accounts (scoped to this company)
      - Open fiscal year + period
    Writes audit log: action = create_journal_draft_via_gemini
    """
    # ── Role check (raises 403 if not admin/accountant — intentional HTTP error) ─
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
        allowed_roles={"admin", "accountant"},
    )

    if payload.action_type != "create_journal_entry_draft":
        return ConfirmActionReply(
            success=False,
            error_code="unsupported_action",
            message="Unsupported action type.",
        )

    jp = payload.payload

    # ── Enforce backend-derived today ────────────────────────────────────────
    from app.core.clock import get_today_date
    today = get_today_date()
    if jp.entry_date != today:
        return ConfirmActionReply(
            success=False,
            error_code="gemini_date_must_be_today",
            message=(
                "Gemini Assistant can only create entries for today's date. "
                f"Expected {today}, received {jp.entry_date}."
            ),
        )

    # ── Validate company ─────────────────────────────────────────────────────
    company = get_company_or_none(db=db, company_id=payload.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    # ── Validate accounts ────────────────────────────────────────────────────
    for line in jp.lines:
        account = get_account(db=db, account_id=line.account_id)
        if not account or account.company_id != payload.company_id:
            return ConfirmActionReply(
                success=False,
                error_code="account_not_found",
                message=f"Account {line.account_id} not found or does not belong to this company.",
            )
        if not account.is_active:
            return ConfirmActionReply(
                success=False,
                error_code="account_inactive",
                message=f"Account {line.account_id} ({account.name}) is inactive.",
            )

    # ── Validate balanced entry ──────────────────────────────────────────────
    total_debit = sum(line.debit for line in jp.lines)
    total_credit = sum(line.credit for line in jp.lines)
    if total_debit <= 0:
        return ConfirmActionReply(
            success=False,
            error_code="unbalanced_entry",
            message="Total debit must be greater than zero.",
        )
    if total_debit != total_credit:
        return ConfirmActionReply(
            success=False,
            error_code="unbalanced_entry",
            message="Journal entry must be balanced (total debit = total credit).",
        )

    # ── Validate fiscal year ─────────────────────────────────────────────────
    fiscal_year = find_fiscal_year_for_date(
        db=db, company_id=payload.company_id, entry_date=jp.entry_date,
    )
    if not fiscal_year:
        open_period_suggestion = _find_open_period_suggestion(db, payload.company_id)
        return ConfirmActionReply(
            success=False,
            error_code="fiscal_year_not_found",
            message=(
                f"No fiscal year found for the entry date {jp.entry_date}. "
                "Please choose a date within an existing fiscal year."
            ),
            open_period_suggestion=open_period_suggestion,
        )
    if fiscal_year.status != "open":
        open_period_suggestion = _find_open_period_suggestion(db, payload.company_id)
        return ConfirmActionReply(
            success=False,
            error_code="fiscal_year_closed",
            message=(
                f"The fiscal year for {jp.entry_date} is not open (status: {fiscal_year.status}). "
                "Please choose a date within an open fiscal year."
            ),
            open_period_suggestion=open_period_suggestion,
        )

    # ── Validate fiscal period ───────────────────────────────────────────────
    fiscal_period = find_fiscal_period_for_date(
        db=db, company_id=payload.company_id, entry_date=jp.entry_date,
    )
    if not fiscal_period:
        open_period_suggestion = _find_open_period_suggestion(db, payload.company_id)
        return ConfirmActionReply(
            success=False,
            error_code="today_not_in_open_fiscal_period",
            message=(
                f"No open fiscal period found for today's date ({jp.entry_date}). "
                "Open or create a fiscal period that includes today's date."
            ),
            open_period_suggestion=open_period_suggestion,
        )
    if fiscal_period.status != "open":
        open_period_suggestion = _find_open_period_suggestion(db, payload.company_id)
        return ConfirmActionReply(
            success=False,
            error_code="today_not_in_open_fiscal_period",
            message=(
                f"The fiscal period for today's date ({jp.entry_date}) is closed. "
                "Open or create a fiscal period that includes today's date."
            ),
            open_period_suggestion=open_period_suggestion,
        )

    # ── Generate unique entry_no ─────────────────────────────────────────────
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    base_entry_no = f"AI-{ts}"
    entry_no = base_entry_no
    suffix = 0
    while get_journal_entry_by_no(db=db, company_id=payload.company_id, entry_no=entry_no):
        suffix += 1
        entry_no = f"{base_entry_no}-{suffix}"

    # ── Create journal entry ─────────────────────────────────────────────────
    journal_create = JournalEntryCreate(
        company_id=payload.company_id,
        entry_no=entry_no,
        entry_date=jp.entry_date,
        description=jp.description,
        source_type="gemini_assistant",
        source_id=None,
        lines=[
            JournalLineCreate(
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
                description=line.description,
            )
            for line in jp.lines
        ],
    )

    journal_entry = create_journal_entry(
        db=db,
        payload=journal_create,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
    )

    # ── Audit log (best-effort: journal entry already committed) ────────────
    try:
        create_audit_log(
            db=db,
            company_id=journal_entry.company_id,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action="create_journal_draft_via_gemini",
            entity_type="journal_entry",
            entity_id=journal_entry.id,
            description=f"Created draft journal entry via Gemini Assistant: {journal_entry.entry_no}",
            old_values=None,
            new_values={
                "entry_no": journal_entry.entry_no,
                "entry_date": str(journal_entry.entry_date),
                "description": journal_entry.description,
                "status": journal_entry.status,
                "source_type": "gemini_assistant",
                "total_debit": str(total_debit),
            },
        )
    except Exception:
        # Journal entry is already committed — log full traceback server-side
        # but don't fail the user response or expose internal details
        logging.getLogger(__name__).exception(
            "Audit log write failed for Gemini journal entry %s (id=%s). "
            "The journal entry was created successfully but the audit trail is incomplete.",
            journal_entry.entry_no,
            journal_entry.id,
        )

    return ConfirmActionReply(
        success=True,
        message=f"Draft journal entry {journal_entry.entry_no} created successfully.",
        entity_id=journal_entry.id,
        entity_type="journal_entry",
        data={"entry_no": journal_entry.entry_no, "status": journal_entry.status},
    )


def _find_open_period_suggestion(db, company_id: int) -> str | None:
    """
    Return the start_date of the first open fiscal period for this company
    as an ISO date string, to suggest a valid date to the user.
    Returns None if no open period exists.
    """
    from app.modules.accounting.services.fiscal_service import list_fiscal_periods
    try:
        periods = list_fiscal_periods(db=db, company_id=company_id, limit=50)
        open_periods = [p for p in periods if p.status == "open"]
        if open_periods:
            return str(open_periods[0].start_date)
        return None
    except Exception:
        return None


