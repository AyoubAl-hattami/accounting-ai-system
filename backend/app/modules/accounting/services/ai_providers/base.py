"""
Base class for AI journal suggestion providers.

.. deprecated::
    Use the ``JournalSuggestionProvider`` Protocol from
    ``app.application.ai.ports`` for new provider implementations.
    New providers should be placed in ``app/infrastructure/ai/providers/``.
    This ABC shim is retained for the existing provider subclasses.
"""

from abc import ABC, abstractmethod

from app.application.ai.dto import AccountInfoDTO


class BaseJournalSuggestionProvider(ABC):
    """Base class for all journal suggestion providers (legacy ABC shim)."""

    @abstractmethod
    def suggest_journal_entry(
        self,
        description: str,
        accounts: list[AccountInfoDTO],
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
