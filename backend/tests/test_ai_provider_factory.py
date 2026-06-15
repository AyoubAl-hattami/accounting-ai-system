"""
Unit tests for the AI provider factory and providers.

These tests do not require a running backend server — they test
the provider classes and factory logic directly.
All OpenAI tests use mocking — no real API calls are made.
"""

import json
from unittest.mock import patch, MagicMock

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
from app.modules.accounting.services.ai_providers.openai_provider import (
    OpenAIJournalSuggestionProvider,
    _validate_account_id,
    _validate_amount,
    _validate_confidence,
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


# ── Rules Provider Tests ─────────────────────────────────────────────────────


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


# ── LLM Placeholder Tests ────────────────────────────────────────────────────


def test_llm_placeholder_delegates_to_rules():
    provider = LlmPlaceholderJournalSuggestionProvider()
    assert provider.provider_name == "llm_placeholder"
    assert provider.source_label == "llm_placeholder_fallback"

    result = provider.suggest_journal_entry(
        description="Paid rent from bank for 1000",
        accounts=SAMPLE_ACCOUNTS,
        language="en",
    )

    assert result["detected_intent"] == "rent_lease"
    assert result["amount"] == 1000.0
    assert result["source"] == "llm_placeholder_fallback"
    assert any("LLM provider is not configured" in w for w in result["warnings"])


def test_llm_placeholder_does_not_call_external_services():
    provider = LlmPlaceholderJournalSuggestionProvider()
    result = provider.suggest_journal_entry(
        description="Paid rent from bank for 1000",
        accounts=SAMPLE_ACCOUNTS,
        language="en",
    )
    assert result is not None
    assert isinstance(result, dict)


# ── Factory Tests ─────────────────────────────────────────────────────────────


def test_factory_returns_rules_provider_by_default():
    provider = get_journal_suggestion_provider()
    assert provider.provider_name == "rules"


def test_factory_known_providers_registry():
    assert "rules" in _PROVIDERS
    assert "llm_placeholder" in _PROVIDERS
    assert "openai" in _PROVIDERS


def test_provider_status_default_is_rules():
    status = get_provider_status()
    assert status["journal_provider"] == "rules"
    assert status["llm_enabled"] is False
    assert status["fallback_enabled"] is True
    assert status["source"] == "backend_rules"
    assert isinstance(status["message"], str)


# ── OpenAI Provider Tests (All Mocked) ────────────────────────────────────────


def test_openai_provider_selected_when_configured():
    """OpenAI provider is returned when AI_JOURNAL_PROVIDER=openai and key is set."""
    mock_settings = MagicMock()
    mock_settings.AI_JOURNAL_PROVIDER = "openai"
    mock_settings.OPENAI_API_KEY = "sk-test-fake-key-12345"
    mock_settings.OPENAI_MODEL = "gpt-4o-mini"

    with patch(
        "app.modules.accounting.services.ai_provider_factory.settings",
        mock_settings,
    ), patch(
        "app.modules.accounting.services.ai_providers.openai_provider.settings",
        mock_settings,
    ):
        provider = get_journal_suggestion_provider()
        assert provider.provider_name == "openai"


def test_openai_provider_falls_back_when_key_missing():
    """OpenAI provider returns rules fallback when API key is empty."""
    mock_settings = MagicMock()
    mock_settings.AI_JOURNAL_PROVIDER = "openai"
    mock_settings.OPENAI_API_KEY = ""
    mock_settings.OPENAI_MODEL = "gpt-4o-mini"

    with patch(
        "app.modules.accounting.services.ai_provider_factory.settings",
        mock_settings,
    ), patch(
        "app.modules.accounting.services.ai_providers.openai_provider.settings",
        mock_settings,
    ):
        provider = get_journal_suggestion_provider()
        result = provider.suggest_journal_entry(
            description="Paid rent from bank for 1000",
            accounts=SAMPLE_ACCOUNTS,
            language="en",
        )

        assert result["source"] == "openai_fallback_rules"
        assert result["detected_intent"] == "rent_lease"
        assert result["amount"] == 1000.0
        assert any("not configured" in w.lower() for w in result["warnings"])


def test_openai_provider_returns_validated_output_on_valid_response():
    """OpenAI provider returns validated output when mocked response is valid."""
    mock_settings = MagicMock()
    mock_settings.OPENAI_API_KEY = "sk-test-fake-key-12345"
    mock_settings.OPENAI_MODEL = "gpt-4o-mini"

    valid_json = json.dumps({
        "debit_account_id": 11,
        "credit_account_id": 2,
        "amount": 1000.0,
        "confidence": "high",
        "explanation": "Rent is an expense, debit Rent Expense, credit Main Bank.",
        "warnings": [],
        "detected_intent": "rent_lease",
    })

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = valid_json

    with patch(
        "app.modules.accounting.services.ai_providers.openai_provider.settings",
        mock_settings,
    ):
        provider = OpenAIJournalSuggestionProvider()

        with patch(
            "app.modules.accounting.services.ai_providers.openai_provider.OpenAI"
        ) as mock_openai_class:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            result = provider.suggest_journal_entry(
                description="Paid rent from bank for 1000",
                accounts=SAMPLE_ACCOUNTS,
                language="en",
            )

    assert result["source"] == "openai"
    assert result["debit_account_id"] == 11
    assert result["credit_account_id"] == 2
    assert result["amount"] == 1000.0
    assert result["confidence"] == "high"
    assert result["detected_intent"] == "rent_lease"


def test_openai_provider_rejects_invalid_account_ids():
    """OpenAI provider rejects account IDs not in available accounts."""
    mock_settings = MagicMock()
    mock_settings.OPENAI_API_KEY = "sk-test-fake-key-12345"
    mock_settings.OPENAI_MODEL = "gpt-4o-mini"

    # Account ID 999 does not exist in SAMPLE_ACCOUNTS
    invalid_json = json.dumps({
        "debit_account_id": 999,
        "credit_account_id": 2,
        "amount": 500.0,
        "confidence": "medium",
        "explanation": "Some explanation.",
        "warnings": [],
        "detected_intent": "purchase_equipment",
    })

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = invalid_json

    with patch(
        "app.modules.accounting.services.ai_providers.openai_provider.settings",
        mock_settings,
    ):
        provider = OpenAIJournalSuggestionProvider()

        with patch(
            "app.modules.accounting.services.ai_providers.openai_provider.OpenAI"
        ) as mock_openai_class:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            result = provider.suggest_journal_entry(
                description="Bought equipment for 500",
                accounts=SAMPLE_ACCOUNTS,
                language="en",
            )

    assert result["source"] == "openai"
    assert result["debit_account_id"] is None  # Rejected
    assert result["credit_account_id"] == 2  # Valid
    assert any("999" in w and "not in" in w for w in result["warnings"])


def test_openai_provider_falls_back_on_invalid_json():
    """OpenAI provider falls back to rules when model returns invalid JSON."""
    mock_settings = MagicMock()
    mock_settings.OPENAI_API_KEY = "sk-test-fake-key-12345"
    mock_settings.OPENAI_MODEL = "gpt-4o-mini"

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is not valid JSON at all."

    with patch(
        "app.modules.accounting.services.ai_providers.openai_provider.settings",
        mock_settings,
    ):
        provider = OpenAIJournalSuggestionProvider()

        with patch(
            "app.modules.accounting.services.ai_providers.openai_provider.OpenAI"
        ) as mock_openai_class:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            result = provider.suggest_journal_entry(
                description="Paid rent from bank for 1000",
                accounts=SAMPLE_ACCOUNTS,
                language="en",
            )

    assert result["source"] == "openai_fallback_rules"
    assert result["detected_intent"] == "rent_lease"
    assert any("invalid output" in w.lower() or "fallback" in w.lower() for w in result["warnings"])


def test_openai_provider_falls_back_on_exception():
    """OpenAI provider falls back to rules when OpenAI client raises exception."""
    mock_settings = MagicMock()
    mock_settings.OPENAI_API_KEY = "sk-test-fake-key-12345"
    mock_settings.OPENAI_MODEL = "gpt-4o-mini"

    with patch(
        "app.modules.accounting.services.ai_providers.openai_provider.settings",
        mock_settings,
    ):
        provider = OpenAIJournalSuggestionProvider()

        with patch(
            "app.modules.accounting.services.ai_providers.openai_provider.OpenAI"
        ) as mock_openai_class:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception(
                "Connection refused"
            )
            mock_openai_class.return_value = mock_client

            result = provider.suggest_journal_entry(
                description="Paid rent from bank for 1000",
                accounts=SAMPLE_ACCOUNTS,
                language="en",
            )

    assert result["source"] == "openai_fallback_rules"
    assert result["detected_intent"] == "rent_lease"
    assert result["amount"] == 1000.0
    assert any("unavailable" in w.lower() or "fallback" in w.lower() for w in result["warnings"])


def test_openai_status_shows_llm_enabled_when_configured():
    """GET /ai/status shows llm_enabled true when OpenAI is configured."""
    mock_settings = MagicMock()
    mock_settings.AI_JOURNAL_PROVIDER = "openai"
    mock_settings.OPENAI_API_KEY = "sk-test-fake-key-12345"
    mock_settings.OPENAI_MODEL = "gpt-4o-mini"

    with patch(
        "app.modules.accounting.services.ai_provider_factory.settings",
        mock_settings,
    ), patch(
        "app.modules.accounting.services.ai_providers.openai_provider.settings",
        mock_settings,
    ):
        status = get_provider_status()

    assert status["journal_provider"] == "openai"
    assert status["llm_enabled"] is True
    assert status["fallback_enabled"] is True
    assert status["source"] == "openai"
    assert "OpenAI provider is active" in status["message"]


def test_openai_status_shows_fallback_when_key_missing():
    """GET /ai/status shows fallback when OpenAI key is missing."""
    mock_settings = MagicMock()
    mock_settings.AI_JOURNAL_PROVIDER = "openai"
    mock_settings.OPENAI_API_KEY = ""
    mock_settings.OPENAI_MODEL = "gpt-4o-mini"

    with patch(
        "app.modules.accounting.services.ai_provider_factory.settings",
        mock_settings,
    ), patch(
        "app.modules.accounting.services.ai_providers.openai_provider.settings",
        mock_settings,
    ):
        status = get_provider_status()

    assert status["journal_provider"] == "openai"
    assert status["llm_enabled"] is False
    assert status["source"] == "openai_fallback_rules"
    assert "not configured" in status["message"]


# ── Validation Helper Tests ───────────────────────────────────────────────────


def test_validate_confidence_accepts_valid_values():
    assert _validate_confidence("high") == "high"
    assert _validate_confidence("medium") == "medium"
    assert _validate_confidence("low") == "low"


def test_validate_confidence_rejects_invalid_values():
    assert _validate_confidence("very_high") == "low"
    assert _validate_confidence("") == "low"
    assert _validate_confidence("HIGH") == "low"


def test_validate_amount_handles_valid_amounts():
    assert _validate_amount(1000.0) == 1000.0
    assert _validate_amount(1000) == 1000.0
    assert _validate_amount("500.50") == 500.50


def test_validate_amount_handles_invalid_amounts():
    assert _validate_amount(None) is None
    assert _validate_amount(-100) is None
    assert _validate_amount(0) is None
    assert _validate_amount("not_a_number") is None


def test_validate_account_id_accepts_valid_ids():
    warnings = []
    result = _validate_account_id(2, SAMPLE_ACCOUNTS, "debit", warnings)
    assert result == 2
    assert len(warnings) == 0


def test_validate_account_id_rejects_unknown_ids():
    warnings = []
    result = _validate_account_id(999, SAMPLE_ACCOUNTS, "debit", warnings)
    assert result is None
    assert len(warnings) == 1
    assert "999" in warnings[0]
