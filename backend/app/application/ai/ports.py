"""AI journal suggestion provider port.

Defined as ``typing.Protocol`` — never ABC — so the application layer remains
framework-neutral.
"""

from __future__ import annotations

from typing import Protocol

from app.application.ai.dto import AccountInfoDTO


class JournalSuggestionProvider(Protocol):
    """Stateless provider that generates a journal entry suggestion from text."""

    @property
    def provider_name(self) -> str: ...

    @property
    def source_label(self) -> str: ...

    def suggest_journal_entry(
        self,
        description: str,
        accounts: list[AccountInfoDTO],
        language: str = "en",
    ) -> dict: ...
