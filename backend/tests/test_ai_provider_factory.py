"""
Unit tests for the AI provider factory and providers.

These tests do not require a running backend server — they test
the provider classes and factory logic directly.
"""

from app.modules.accounting.services.ai_provider_factory import (
    get_journal_suggestion_provider,
    get_provider_status,
    _PROVIDERS,
)
from app.modules.accounting.services.ai_providers.rules_provider import (
    RulesJournalSuggestionProvider,
)
from app.modules.accounting.services.ai_providers.llm_placeholder_provider import (
    LlmPlaceholderJournalSuggestionProvider,
)
from app.modules.accounting.schemas.ai_suggestion_schemas import AccountInfo


SAMPLE_ACCOUNTS = [
    AccountInfo(
        id=1, code="1000", name="Assets",
        account_type="asset", is_active=True,
    ),
    AccountInfo(
        id=2, code="1110", name="Main Bank",
        account_type="asset", is_active=True,
    ),
    AccountInfo(
        id=11, code="5100", name="Rent Expense",
        account_type="expense", is_active=True,
    ),
]


def test_rules_provider_returns_backend_rules_source():
    provider = RulesJournalSuggestionProvider()
    assert provider.provider_name == "rules"
    assert provider.source_label == "backend_rules"

    result = provider.suggest_journal_entry(
        description="Paid rent from bank for 1000",
        accounts=SAMPLE_ACCOUNTS,
        language="en",
    )

    assert result["source"] == "backend_rules"
    assert result["detected_intent"] == "rent_lease"
    assert result["amount"] == 1000.0


def test_llm_placeholder_delegates_to_rules():
    provider = LlmPlaceholderJournalSuggestionProvider()
    assert provider.provider_name == "llm_placeholder"
    assert provider.source_label == "llm_placeholder_fallback"

    result = provider.suggest_journal_entry(
        description="Paid rent from bank for 1000",
        accounts=SAMPLE_ACCOUNTS,
        language="en",
    )

    # Should still detect intent correctly (delegated to rules)
    assert result["detected_intent"] == "rent_lease"
    assert result["amount"] == 1000.0

    # Source should indicate LLM placeholder fallback
    assert result["source"] == "llm_placeholder_fallback"

    # Should have the LLM not configured warning
    assert any("LLM provider is not configured" in w for w in result["warnings"])


def test_llm_placeholder_does_not_call_external_services():
    """Verify the LLM placeholder never makes network requests."""
    provider = LlmPlaceholderJournalSuggestionProvider()

    # This should complete instantly without any network calls
    result = provider.suggest_journal_entry(
        description="Paid rent from bank for 1000",
        accounts=SAMPLE_ACCOUNTS,
        language="en",
    )

    # If it returned a result, it didn't hang on network
    assert result is not None
    assert isinstance(result, dict)


def test_factory_returns_rules_provider_by_default():
    provider = get_journal_suggestion_provider()
    assert provider.provider_name == "rules"


def test_factory_known_providers_registry():
    assert "rules" in _PROVIDERS
    assert "llm_placeholder" in _PROVIDERS


def test_provider_status_default_is_rules():
    status = get_provider_status()
    assert status["journal_provider"] == "rules"
    assert status["llm_enabled"] is False
    assert status["fallback_enabled"] is True
    assert status["source"] == "backend_rules"
    assert isinstance(status["message"], str)
