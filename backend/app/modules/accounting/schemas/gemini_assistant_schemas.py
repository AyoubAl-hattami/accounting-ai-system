"""
Pydantic schemas for the Gemini Assistant endpoints.

POST /ai/gemini-assistant              - ask a question or request a suggested action
POST /ai/gemini-assistant/confirm-action - execute a pre-approved action (create journal draft)
"""

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


# ── Page context ──────────────────────────────────────────────────────────────

class PageFilters(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    account_id: int | None = None
    status: str | None = None


class PageContext(BaseModel):
    route: str = Field(default="/dashboard", max_length=200)
    page: str = Field(default="dashboard", max_length=100)
    filters: PageFilters = Field(default_factory=PageFilters)


# ── Conversation history (sent by frontend for follow-up context) ─────────────

class ConversationTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=2000)


# ── Gemini Assistant request ──────────────────────────────────────────────────

class GeminiAssistantRequest(BaseModel):
    company_id: int = Field(..., ge=1)
    message: str = Field(..., min_length=1, max_length=2000)
    page_context: PageContext = Field(default_factory=PageContext)
    language: str = Field(default="en", pattern="^(en|ar)$")
    # Last N turns for follow-up context (not persisted)
    history: list[ConversationTurn] = Field(default_factory=list, max_length=6)


# ── Suggested action (journal draft) ─────────────────────────────────────────

class SuggestedJournalLine(BaseModel):
    account_id: int
    account_name: str
    account_code: str
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")
    description: str | None = None


class SuggestedJournalPayload(BaseModel):
    entry_date: date
    description: str
    lines: list[SuggestedJournalLine]
    amount: float | None = None
    warnings: list[str] = Field(default_factory=list)
    # Pre-validation: set to False when entry_date has no open fiscal period
    fiscal_period_valid: bool = True
    open_period_suggestion: str | None = None  # suggested date within open period


class SuggestedAction(BaseModel):
    type: str  # "create_journal_entry_draft"
    requires_confirmation: bool = True
    payload: SuggestedJournalPayload


# ── Gemini Assistant response ─────────────────────────────────────────────────

class GeminiAssistantReply(BaseModel):
    reply: str
    intent: str  # e.g. "answer_report_question", "create_journal_draft", "access_denied", "clarification"
    confidence: str = Field(default="medium", pattern="^(high|medium|low)$")
    data_sources: list[str] = Field(default_factory=list)
    suggested_action: SuggestedAction | None = None


# ── Confirm-action request ────────────────────────────────────────────────────

class ConfirmJournalLinePayload(BaseModel):
    account_id: int = Field(..., ge=1)
    debit: Decimal = Field(default=Decimal("0.00"), ge=0)
    credit: Decimal = Field(default=Decimal("0.00"), ge=0)
    description: str | None = None


class ConfirmJournalPayload(BaseModel):
    company_id: int = Field(..., ge=1)
    entry_date: date
    description: str = Field(..., min_length=1, max_length=500)
    lines: list[ConfirmJournalLinePayload] = Field(..., min_length=2)


class ConfirmActionRequest(BaseModel):
    company_id: int = Field(..., ge=1)
    action_type: str = Field(..., pattern="^create_journal_entry_draft$")
    payload: ConfirmJournalPayload


# ── Confirm-action response ───────────────────────────────────────────────────

# Structured error codes for confirm-action validation failures
GEMINI_ASSISTANT_ERROR_CODES = {
    "fiscal_period_not_found",
    "fiscal_period_closed",
    "fiscal_year_not_found",
    "fiscal_year_closed",
    "account_inactive",
    "account_not_found",
    "unbalanced_entry",
    "permission_denied",
    "unsupported_action",
    "unknown_error",
}


class ConfirmActionReply(BaseModel):
    success: bool
    message: str
    error_code: str | None = None          # set on failure (see GEMINI_ASSISTANT_ERROR_CODES)
    open_period_suggestion: str | None = None  # ISO date string of a valid open period date
    entity_id: int | None = None
    entity_type: str | None = None
    data: dict[str, Any] | None = None
