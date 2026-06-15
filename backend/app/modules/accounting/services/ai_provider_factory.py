"""
AI provider factory.

Resolves the active journal suggestion provider based on configuration.
Always falls back to the rules provider if the configured provider
is invalid, unavailable, or encounters an error during initialization.
"""

from app.core.config import settings
from app.modules.accounting.services.ai_providers.base import (
    BaseJournalSuggestionProvider,
)
from app.modules.accounting.services.ai_providers.rules_provider import (
    RulesJournalSuggestionProvider,
)
from app.modules.accounting.services.ai_providers.llm_placeholder_provider import (
    LlmPlaceholderJournalSuggestionProvider,
)


_PROVIDERS: dict[str, type[BaseJournalSuggestionProvider]] = {
    "rules": RulesJournalSuggestionProvider,
    "llm_placeholder": LlmPlaceholderJournalSuggestionProvider,
}


def get_journal_suggestion_provider() -> BaseJournalSuggestionProvider:
    """
    Return the configured journal suggestion provider.

    Falls back to rules provider if:
    - AI_JOURNAL_PROVIDER is not set
    - AI_JOURNAL_PROVIDER has an invalid/unknown value
    - Provider initialization fails for any reason
    """
    provider_key = getattr(settings, "AI_JOURNAL_PROVIDER", "rules").strip().lower()

    provider_class = _PROVIDERS.get(provider_key)

    if provider_class is None:
        # Unknown provider — fall back to rules
        return RulesJournalSuggestionProvider()

    try:
        return provider_class()
    except Exception:
        # Provider initialization failed — fall back to rules
        return RulesJournalSuggestionProvider()


def get_provider_status() -> dict:
    """
    Return the current AI provider status for the status endpoint.
    """
    provider = get_journal_suggestion_provider()
    provider_key = getattr(settings, "AI_JOURNAL_PROVIDER", "rules").strip().lower()

    is_rules = provider.provider_name == "rules"

    if is_rules and provider_key == "rules":
        message = "Backend rules provider is active."
    elif provider.provider_name == "llm_placeholder":
        message = "LLM provider is not configured. Backend rules fallback is active."
    else:
        # Fallback case (invalid config resolved to rules)
        message = "Backend rules provider is active (fallback from invalid config)."

    return {
        "journal_provider": provider.provider_name,
        "llm_enabled": False,
        "fallback_enabled": True,
        "source": provider.source_label,
        "message": message,
    }
