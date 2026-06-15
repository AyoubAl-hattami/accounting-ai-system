"""
Rules-based journal suggestion provider.

Wraps the existing deterministic rules engine from ai_suggestion_service
into the provider interface. This is the default and safe fallback provider.
"""

from app.modules.accounting.schemas.ai_suggestion_schemas import AccountInfo
from app.modules.accounting.services.ai_providers.base import (
    BaseJournalSuggestionProvider,
)
from app.modules.accounting.services.ai_suggestion_service import (
    suggest_journal_entry as rules_suggest,
)


class RulesJournalSuggestionProvider(BaseJournalSuggestionProvider):
    """Deterministic rules-based provider using regex intent detection."""

    def suggest_journal_entry(
        self,
        description: str,
        accounts: list[AccountInfo],
        language: str = "en",
    ) -> dict:
        return rules_suggest(
            description=description,
            accounts=accounts,
            language=language,
        )

    @property
    def provider_name(self) -> str:
        return "rules"

    @property
    def source_label(self) -> str:
        return "backend_rules"
