"""
Pydantic schemas for the Gemini Assistant endpoints.

POST /ai/gemini-assistant              - ask a question or request a suggested action
POST /ai/gemini-assistant/confirm-action - execute a pre-approved action (create journal draft)
"""

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Semantic transaction parsing (internal) ───────────────────────────────────

class ParsedTransaction(BaseModel):
    """Structured output from Gemini semantic transaction parser."""
    intent: Literal["create_journal_entry", "clarification", "not_accounting"] = "not_accounting"
    transaction_type: str = "unknown"  # expense_payment, income_receipt, etc.
    amount: float | None = None
    description: str = ""
    debit_account_hint: str | None = None
    credit_account_hint: str | None = None
    income_or_expense_nature: str | None = None  # electricity, rent, salary, etc.
    counterparty: str | None = None
    payment_source_hint: str | None = None  # bank, cash, unknown
    receiving_account_hint: str | None = None
    confidence: float = 0.0
    needs_clarification: bool = False
    clarification_question: str | None = None
    clarification_options: list[str] = Field(default_factory=list)


class MappedTransaction(BaseModel):
    """Result of mapping ParsedTransaction hints to real company accounts."""
    debit_account_id: int | None = None
    debit_account_name: str | None = None
    debit_account_code: str | None = None
    credit_account_id: int | None = None
    credit_account_name: str | None = None
    credit_account_code: str | None = None
    amount: float | None = None
    description: str = ""
    needs_clarification: bool = False
    clarification_question: str | None = None
    clarification_options: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ClarificationOption(BaseModel):
    """Structured answer option for a pending clarification."""
    label: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1, max_length=100)


class PendingTransaction(BaseModel):
    """Server-derived transaction state awaiting a clarification answer."""
    company_id: int = Field(..., ge=1)
    transaction_type: str = Field(default="unknown", max_length=80)
    amount: float = Field(..., gt=0)
    description: str = Field(default="", max_length=500)
    debit_account_hint: str | None = Field(default=None, max_length=200)
    credit_account_hint: str | None = Field(default=None, max_length=200)
    income_or_expense_nature: str | None = Field(default=None, max_length=120)
    counterparty: str | None = Field(default=None, max_length=200)
    payment_source_hint: str | None = Field(default=None, max_length=80)
    receiving_account_hint: str | None = Field(default=None, max_length=80)
    missing_fields: list[str] = Field(default_factory=list, max_length=5)


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
    pending_transaction: PendingTransaction | None = None
    pending_context_token: str | None = Field(default=None, max_length=8000)


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


# ── Evidence (structured data backing an answer) ──────────────────────────────

class EvidenceEntry(BaseModel):
    """Structured evidence entry returned alongside Gemini answers."""
    entry_no: str | None = None
    date: str | None = None
    amount: float | None = None
    debit_account: str | None = None
    credit_account: str | None = None
    status: str | None = None
    actor_name: str | None = None
    description: str | None = None


class ProfitAndLossPeriod(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    label: str


class ProfitAndLossMetrics(BaseModel):
    revenue: str
    expenses: str
    net_profit: str


class ProfitAndLossReference(BaseModel):
    type: Literal["report"]
    report: Literal["profit_and_loss"]
    filters: dict[str, str] = Field(default_factory=dict)


class ProfitAndLossGrounding(BaseModel):
    status: Literal["grounded", "unavailable"]
    kind: Literal["profit_and_loss"]
    requested_metric: Literal["revenue", "expenses", "net_profit"] | None = None
    period: ProfitAndLossPeriod | None = None
    metrics: ProfitAndLossMetrics | None = None
    reference: ProfitAndLossReference | None = None

# ── Gemini Assistant response ─────────────────────────────────────────────────

class JournalEvidenceEntry(BaseModel):
    journal_entry_id: int
    entry_number: str
    entry_date: str
    description: str | None = None
    status: str
    source: str
    creator_name: str
    total_debit: str
    total_credit: str
    matched_amount: str | None = None
    match_reason: Literal["debit_line", "credit_line", "total_debit", "total_credit", "report_revenue_contribution", "report_expense_contribution"]


class JournalEvidenceSummary(BaseModel):
    total_matches: int
    returned_matches: int
    has_more: bool


class JournalEvidenceGrounding(BaseModel):
    status: Literal["grounded", "unavailable"]
    kind: Literal["journal_evidence"]
    basis: Literal["amount_trace", "profit_and_loss_contribution"] | None = None
    metric: Literal["revenue", "expenses", "net_profit"] | None = None
    period: ProfitAndLossPeriod | None = None
    query: dict[str, str] = Field(default_factory=dict)
    summary: JournalEvidenceSummary | None = None
    entries: list[JournalEvidenceEntry] = Field(default_factory=list)

class ReportPeriod(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    as_of_date: str | None = None
    label: str

class ReportReference(BaseModel):
    type: Literal["report"]
    report: Literal["balance_sheet", "trial_balance", "account_ledger", "general_ledger"]
    filters: dict[str, str | int | None] = Field(default_factory=dict)

class ReportSummary(BaseModel):
    total_accounts: int = 0
    returned_accounts: int = 0
    total_entries: int = 0
    returned_entries: int = 0
    has_more: bool = False

class BalanceSheetGrounding(BaseModel):
    status: Literal["grounded", "unavailable"]
    kind: Literal["balance_sheet"]
    requested_metric: Literal["assets", "liabilities", "equity", "current_year_earnings", "prior_year_earnings", "account", "equation"] | None = None
    period: ReportPeriod | None = None
    metrics: dict[str, str | bool] | None = None
    sections: list[dict[str, object]] = Field(default_factory=list)
    reference: ReportReference | None = None

class TrialBalanceGrounding(BaseModel):
    status: Literal["grounded", "unavailable"]
    kind: Literal["trial_balance"]
    requested_metric: Literal["total_debit", "total_credit", "difference", "balanced", "account", "accounts"] | None = None
    period: ReportPeriod | None = None
    metrics: dict[str, str | bool] | None = None
    accounts: list[dict[str, object]] = Field(default_factory=list)
    summary: ReportSummary | None = None
    reference: ReportReference | None = None

class AccountLedgerGrounding(BaseModel):
    status: Literal["grounded", "unavailable"]
    kind: Literal["account_ledger"]
    requested_metric: Literal["balance", "opening_balance", "debits", "credits", "transactions"] | None = None
    period: ReportPeriod | None = None
    account: dict[str, object] | None = None
    metrics: dict[str, str] | None = None
    entries: list[dict[str, object]] = Field(default_factory=list)
    summary: ReportSummary | None = None
    reference: ReportReference | None = None

class GeneralLedgerGrounding(BaseModel):
    status: Literal["grounded", "unavailable"]
    kind: Literal["general_ledger"]
    requested_metric: Literal["accounts", "balances", "transactions"] | None = None
    period: ReportPeriod | None = None
    accounts: list[dict[str, object]] = Field(default_factory=list)
    summary: ReportSummary | None = None
    reference: ReportReference | None = None
class GeminiAssistantReply(BaseModel):
    reply: str
    intent: str  # e.g. "answer_report_question", "create_journal_draft", "access_denied", "clarification"
    confidence: str = Field(default="medium", pattern="^(high|medium|low)$")
    data_sources: list[str] = Field(default_factory=list)
    suggested_action: SuggestedAction | None = None
    pending_transaction: PendingTransaction | None = None
    clarification_options: list[ClarificationOption] = Field(default_factory=list)
    pending_context_token: str | None = None
    evidence: list[EvidenceEntry] = Field(default_factory=list)
    grounding: ProfitAndLossGrounding | JournalEvidenceGrounding | BalanceSheetGrounding | TrialBalanceGrounding | AccountLedgerGrounding | GeneralLedgerGrounding | None = None


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
    conversation_id: int | None = Field(default=None, ge=1)
    language: str = Field(default="en", pattern="^(en|ar)$")
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
    "gemini_date_must_be_today",
    "today_not_in_open_fiscal_period",
}


class ConfirmActionReply(BaseModel):
    success: bool
    message: str
    error_code: str | None = None          # set on failure (see GEMINI_ASSISTANT_ERROR_CODES)
    open_period_suggestion: str | None = None  # ISO date string of a valid open period date
    entity_id: int | None = None
    entity_type: str | None = None
    data: dict[str, Any] | None = None
