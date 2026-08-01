"""AI journal suggestion use cases."""

from __future__ import annotations

from app.application.ai.dto import AccountInfoDTO, JournalSuggestionQuery, JournalSuggestionResultDTO
from app.application.ai.ports import JournalSuggestionProvider


class SuggestJournalEntry:
    """Orchestrates a journal suggestion using the configured provider."""

    def __init__(self, provider: JournalSuggestionProvider) -> None:
        self._provider = provider

    def execute(self, query: JournalSuggestionQuery) -> dict:
        """Return raw dict from the provider (normalized by the caller)."""
        return self._provider.suggest_journal_entry(
            description=query.description,
            accounts=list(query.accounts),
            language=query.language,
        )
