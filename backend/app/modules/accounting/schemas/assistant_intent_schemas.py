"""Strict provider-neutral schemas for assistant intent orchestration."""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


AssistantIntent = Literal[
    "identity",
    "capabilities",
    "greeting",
    "help",
    "unknown",
    "prompt_disclosure",
    "prompt_injection",
    "cross_company_access",
    "fabricate_financial_value",
    "journal_action_boundary",
    "profit_loss_summary",
    "balance_sheet_summary",
    "trial_balance_summary",
    "account_ledger",
    "general_ledger",
    "explain_financial_figure",
    "prepare_journal_draft",
    "confirm_journal_draft",
    "cancel_journal_draft",
    "clarify_transaction",
    "explain_journal",
    "journal_status_question",
    "journal_amount_trace",
    "accounts_question",
    "journals_question",
    "audit_question",
    "who_action_question",
    "company_users_question",
]

AssistantAction = Literal[
    "answer",
    "clarify",
    "refuse",
    "retrieve",
    "explain",
    "prepare_preview",
    "confirm_pending",
    "cancel_pending",
]

AssistantConfidence = Literal["high", "medium", "low"]
AssistantDecisionSource = Literal[
    "deterministic",
    "semantic_provider",
    "conversation_context",
    "legacy_fallback",
]

AssistantTargetHandler = Literal[
    "deterministic_reply",
    "security_refusal",
    "pending_transaction_handler",
    "profit_loss_handler",
    "structured_report_handler",
    "account_ledger_handler",
    "general_ledger_handler",
    "explain_financial_handler",
    "action_request_handler",
    "journal_question_handler",
    "journal_trace_handler",
    "audit_question_handler",
    "who_action_handler",
    "company_users_handler",
    "legacy_classifier",
    "safe_clarification",
]

AssistantMissingField = Literal[
    "account_reference",
    "amount",
    "transaction_meaning",
    "payment_source",
    "receipt_destination",
    "date",
    "report_name",
    "pending_context",
]

PeriodType = Literal[
    "all_available",
    "today",
    "month_to_date",
    "current_month",
    "current_year",
    "custom",
    "as_of",
]

PendingContextType = Literal[
    "none",
    "transaction_clarification",
    "journal_draft_confirmation",
]


class AccountingIntentEntities(BaseModel):
    """Accounting values extracted from user text without inventing missing facts."""

    model_config = ConfigDict(extra="forbid")

    account_reference: str | None = Field(default=None, max_length=200)
    normalized_account_reference: str | None = Field(default=None, max_length=200)
    account_code: str | None = Field(default=None, max_length=50)
    amount: Decimal | None = None
    currency: str | None = Field(default=None, max_length=20)
    transaction_type: str | None = Field(default=None, max_length=80)
    payment_source: str | None = Field(default=None, max_length=80)
    counterparty: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    report_name: str | None = Field(default=None, max_length=80)
    period_type: PeriodType | None = None
    start_date: date | None = None
    end_date: date | None = None
    as_of_date: date | None = None
    journal_reference: str | None = Field(default=None, max_length=100)
    requested_metric: str | None = Field(default=None, max_length=80)
    requested_action: str | None = Field(default=None, max_length=80)

    @field_validator("amount", mode="before")
    @classmethod
    def decimal_amount_only(cls, value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool) or isinstance(value, float):
            raise ValueError("amount must be supplied as a Decimal-safe string")
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("invalid Decimal amount") from exc
        if not amount.is_finite() or amount <= 0:
            raise ValueError("amount must be a positive finite Decimal")
        return amount


class AssistantIntentDecision(BaseModel):
    """One validated orchestration decision with an allowlisted backend target."""

    model_config = ConfigDict(extra="forbid")

    intent: AssistantIntent
    action: AssistantAction
    language: Literal["ar", "en"]
    confidence: AssistantConfidence
    requires_clarification: bool = False
    missing_fields: list[AssistantMissingField] = Field(default_factory=list, max_length=8)
    entities: AccountingIntentEntities = Field(default_factory=AccountingIntentEntities)
    follow_up: bool = False
    source: AssistantDecisionSource
    target_handler: AssistantTargetHandler
    clarification_question: str | None = Field(default=None, max_length=500)


class TrustedIntentConversationContext(BaseModel):
    """Bounded ownership-checked context supplied by the authenticated service."""

    model_config = ConfigDict(extra="forbid")

    same_user: bool = False
    same_company: bool = False
    same_conversation: bool = False
    grounding_status: Literal["grounded", "empty", "unavailable", "malformed", "none"] = "none"
    grounding_kind: Literal[
        "profit_and_loss",
        "balance_sheet",
        "trial_balance",
        "account_ledger",
        "general_ledger",
        "none",
    ] = "none"
    account_reference: str | None = Field(default=None, max_length=200)
    account_code: str | None = Field(default=None, max_length=50)
    pending_context_type: PendingContextType = "none"
    pending_active: bool = False

    @property
    def can_use_grounding(self) -> bool:
        return (
            self.same_user
            and self.same_company
            and self.same_conversation
            and self.grounding_status == "grounded"
        )


class SemanticIntentRequest(BaseModel):
    """Provider input metadata; user and conversation text remain untrusted data."""

    model_config = ConfigDict(extra="forbid")

    latest_user_message: str = Field(..., min_length=1, max_length=2_000)
    language: Literal["ar", "en"]
    bounded_conversation_summary: str | None = Field(default=None, max_length=1_000)
    allowed_intents: tuple[AssistantIntent, ...]
    role_capabilities: tuple[str, ...] = Field(default_factory=tuple, max_length=32)
    pending_context_type: PendingContextType = "none"
