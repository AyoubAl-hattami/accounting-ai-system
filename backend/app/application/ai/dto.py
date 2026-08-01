"""Framework-neutral DTOs for the AI journal suggestion bounded context."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AccountInfoDTO:
    """Minimal account descriptor passed to suggestion providers.

    Replaces the Pydantic ``AccountInfo`` schema so the application layer and
    infrastructure providers remain framework-neutral.
    """

    id: int
    code: str
    name: str
    account_type: str  # "asset" | "liability" | "equity" | "income" | "expense"
    is_active: bool


@dataclass(frozen=True, slots=True)
class JournalSuggestionQuery:
    """Input to the journal suggestion use case."""

    description: str
    accounts: tuple[AccountInfoDTO, ...]
    language: str = "en"


@dataclass(frozen=True, slots=True)
class JournalSuggestionResultDTO:
    """Output of the journal suggestion use case."""

    confidence: str  # "high" | "medium" | "low"
    explanation: str
    warnings: tuple[str, ...]
    detected_intent: str
    source: str
    debit_account_id: int | None = None
    credit_account_id: int | None = None
    amount: float | None = None
