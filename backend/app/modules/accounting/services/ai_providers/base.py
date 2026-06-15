"""
Abstract base class for AI journal suggestion providers.

All providers must implement the suggest_journal_entry method
and return a result dict matching JournalSuggestionResponse fields.
"""

from abc import ABC, abstractmethod

from app.modules.accounting.schemas.ai_suggestion_schemas import AccountInfo


class BaseJournalSuggestionProvider(ABC):
    """Base class for all journal suggestion providers."""

    @abstractmethod
    def suggest_journal_entry(
        self,
        description: str,
        accounts: list[AccountInfo],
        language: str = "en",
    ) -> dict:
        """
        Generate a journal entry suggestion from a natural language description.

        Returns a dict with keys matching JournalSuggestionResponse:
            - debit_account_id: int | None
            - credit_account_id: int | None
            - amount: float | None
            - confidence: str ("high" | "medium" | "low")
            - explanation: str
            - warnings: list[str]
            - detected_intent: str
            - source: str
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier string."""

    @property
    @abstractmethod
    def source_label(self) -> str:
        """Return the source label used in responses."""
