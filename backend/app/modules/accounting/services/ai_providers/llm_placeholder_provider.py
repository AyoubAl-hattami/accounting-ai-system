"""
LLM placeholder journal suggestion provider.

This provider exists solely to prove the provider architecture works.
It does NOT call any external service. It delegates to the rules provider
and adds a warning indicating the LLM is not configured.

In a future phase, this will be replaced with a real LLM integration
(e.g., OpenAI) that processes the description using a language model.
"""

from app.modules.accounting.schemas.ai_suggestion_schemas import AccountInfo
from app.modules.accounting.services.ai_providers.base import (
    BaseJournalSuggestionProvider,
)
from app.modules.accounting.services.ai_providers.rules_provider import (
    RulesJournalSuggestionProvider,
)


class LlmPlaceholderJournalSuggestionProvider(BaseJournalSuggestionProvider):
    """
    Placeholder LLM provider that delegates to rules and adds a warning.

    No external API calls, no API keys, no network requests.
    """

    def __init__(self) -> None:
        self._fallback = RulesJournalSuggestionProvider()

    def suggest_journal_entry(
        self,
        description: str,
        accounts: list[AccountInfo],
        language: str = "en",
    ) -> dict:
        # Delegate to rules provider
        result = self._fallback.suggest_journal_entry(
            description=description,
            accounts=accounts,
            language=language,
        )

        # Override source to indicate LLM placeholder fallback
        result["source"] = "llm_placeholder_fallback"

        # Add warning about LLM not being configured
        warning = (
            "مزود LLM غير مُهيأ. يتم استخدام قواعد الخادم الاحتياطية."
            if language == "ar"
            else "LLM provider is not configured. Using backend rules."
        )
        result["warnings"] = [warning] + result.get("warnings", [])

        return result

    @property
    def provider_name(self) -> str:
        return "llm_placeholder"

    @property
    def source_label(self) -> str:
        return "llm_placeholder_fallback"
