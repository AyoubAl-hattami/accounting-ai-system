"""
OpenAI-backed journal suggestion provider.

Uses the OpenAI Chat Completions API to generate journal entry suggestions
from natural language descriptions. Falls back to the rules provider
on any failure (invalid key, network error, bad model output, etc.).

No API keys are logged or exposed to the frontend.
"""

import json
import logging

# pyrefly: ignore [missing-import]
from openai import OpenAI

from app.core.config import settings
from app.application.ai.dto import AccountInfoDTO as AccountInfo  # noqa: N811
from app.modules.accounting.services.ai_providers.base import (
    BaseJournalSuggestionProvider,
)
from app.modules.accounting.services.ai_providers.rules_provider import (
    RulesJournalSuggestionProvider,
)
from app.modules.accounting.services.gemini_agent_contract import (
    build_agent_prompt,
    default_runtime_context,
    journal_suggestion_task_instructions,
)

logger = logging.getLogger(__name__)


def _build_system_prompt(language: str) -> str:
    """Backward-compatible helper backed by the canonical contract."""
    prompt = build_agent_prompt(
        runtime_context=default_runtime_context(
            language=language,
            provider_name="openai",
        ),
        task_instructions=journal_suggestion_task_instructions(language),
        user_message="",
    )
    return prompt.system_instruction

def _build_user_prompt(
    description: str,
    accounts: list[AccountInfo],
) -> str:
    """Build bounded user/data content while keeping system instructions separate."""
    account_data = [
        {
            "id": account.id,
            "code": account.code,
            "name": account.name,
            "account_type": account.account_type,
        }
        for account in accounts
        if account.is_active
    ]
    prompt = build_agent_prompt(
        runtime_context=default_runtime_context(
            language="en",
            provider_name="openai",
        ),
        task_instructions=journal_suggestion_task_instructions("en"),
        user_message=description,
        trusted_backend_data={"available_current_company_accounts": account_data},
    )
    return prompt.user_message


def _validate_confidence(value: str) -> str:
    """Validate confidence is one of the allowed values."""
    if value in ("high", "medium", "low"):
        return value
    return "low"


def _validate_amount(value) -> float | None:
    """Validate amount is a positive number or None."""
    if value is None:
        return None
    try:
        amount = float(value)
        return amount if amount > 0 else None
    except (TypeError, ValueError):
        return None


def _validate_account_id(
    value,
    accounts: list[AccountInfo],
    field_name: str,
    warnings: list[str],
) -> int | None:
    """Validate account ID exists in the provided accounts list."""
    if value is None:
        return None
    try:
        account_id = int(value)
    except (TypeError, ValueError):
        warnings.append(
            f"Model returned invalid {field_name}: {value}. Set to null."
        )
        return None

    valid_ids = {a.id for a in accounts}
    if account_id not in valid_ids:
        warnings.append(
            f"Model suggested {field_name} {account_id} which is not in "
            f"your chart of accounts. Set to null."
        )
        return None

    return account_id


class OpenAIJournalSuggestionProvider(BaseJournalSuggestionProvider):
    """
    OpenAI-backed journal suggestion provider.

    Falls back to rules provider on any failure.
    """

    def __init__(self) -> None:
        self._fallback = RulesJournalSuggestionProvider()
        self._api_key = getattr(settings, "OPENAI_API_KEY", "").strip()
        self._model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini").strip()
        self._is_configured = bool(self._api_key)

    def suggest_journal_entry(
        self,
        description: str,
        accounts: list[AccountInfo],
        language: str = "en",
    ) -> dict:
        # If API key is not configured, use rules fallback immediately
        if not self._is_configured:
            result = self._fallback.suggest_journal_entry(
                description=description,
                accounts=accounts,
                language=language,
            )
            result["source"] = "openai_fallback_rules"
            result["warnings"] = [
                "OpenAI API key is not configured. Backend rules fallback was used."
            ] + result.get("warnings", [])
            return result

        try:
            return self._call_openai(description, accounts, language)
        except Exception as exc:
            logger.warning(
                "OpenAI provider failed, falling back to rules: %s",
                type(exc).__name__,
            )
            result = self._fallback.suggest_journal_entry(
                description=description,
                accounts=accounts,
                language=language,
            )
            result["source"] = "openai_fallback_rules"
            result["warnings"] = [
                "OpenAI suggestion unavailable. Backend rules fallback was used."
            ] + result.get("warnings", [])
            return result

    def _call_openai(
        self,
        description: str,
        accounts: list[AccountInfo],
        language: str,
    ) -> dict:
        """Make the actual OpenAI API call and validate the response."""
        client = OpenAI(api_key=self._api_key)

        system_prompt = _build_system_prompt(language)
        user_prompt = _build_user_prompt(description, accounts)

        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=800,
        )

        raw_content = response.choices[0].message.content or ""

        # Strip markdown code fences if the model wrapped the JSON
        content = raw_content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines (code fence markers)
            lines = [
                line for line in lines
                if not line.strip().startswith("```")
            ]
            content = "\n".join(lines).strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("OpenAI returned invalid JSON, falling back to rules")
            result = self._fallback.suggest_journal_entry(
                description=description,
                accounts=accounts,
                language=language,
            )
            result["source"] = "openai_fallback_rules"
            result["warnings"] = [
                "OpenAI returned invalid output. Backend rules fallback was used."
            ] + result.get("warnings", [])
            return result

        # Validate and sanitize model output
        warnings: list[str] = []
        if isinstance(parsed.get("warnings"), list):
            warnings.extend(str(w) for w in parsed["warnings"])

        debit_id = _validate_account_id(
            parsed.get("debit_account_id"),
            accounts,
            "debit_account_id",
            warnings,
        )
        credit_id = _validate_account_id(
            parsed.get("credit_account_id"),
            accounts,
            "credit_account_id",
            warnings,
        )
        amount = _validate_amount(parsed.get("amount"))
        confidence = _validate_confidence(
            parsed.get("confidence", "low"),
        )
        explanation = str(parsed.get("explanation", ""))
        detected_intent = str(parsed.get("detected_intent", "unknown"))

        # Normalize confidence based on validated fields, matching rules engine logic.
        # When we have a known intent + both accounts + amount, confidence is "high".
        # When we have a known intent + both accounts but no amount, confidence is "medium".
        if detected_intent != "unknown" and debit_id is not None and credit_id is not None:
            confidence = "high" if amount is not None else "medium"

        return {
            "debit_account_id": debit_id,
            "credit_account_id": credit_id,
            "amount": amount,
            "confidence": confidence,
            "explanation": explanation,
            "warnings": warnings,
            "detected_intent": detected_intent,
            "source": "openai",
        }

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def source_label(self) -> str:
        if self._is_configured:
            return "openai"
        return "openai_fallback_rules"
