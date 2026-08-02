"""
Google Gemini-backed journal suggestion provider.

Uses the Google Generative AI (google-genai) SDK to generate journal entry
suggestions from natural language descriptions. Falls back to the rules
provider on any failure (invalid key, network error, bad model output, etc.).

No API keys are logged or exposed to the frontend.
"""

import json
import logging

from google import genai

from app.core.config import settings
from app.application.ai.dto import AccountInfoDTO as AccountInfo  # noqa: N811
from app.modules.accounting.services.ai_providers.base import (
    BaseJournalSuggestionProvider,
)
from app.modules.accounting.services.ai_providers.rules_provider import (
    RulesJournalSuggestionProvider,
)
from app.modules.accounting.services.gemini_agent_contract import (
    AGENT_CONTRACT_VERSION,
    AgentPrompt,
    build_agent_prompt,
    default_runtime_context,
    journal_suggestion_task_instructions,
)

logger = logging.getLogger(__name__)


def _build_prompt(
    description: str,
    accounts: list[AccountInfo],
    language: str,
) -> AgentPrompt:
    """Build separated canonical instructions and bounded provider data."""
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
    return build_agent_prompt(
        runtime_context=default_runtime_context(
            language=language,
            provider_name="gemini",
        ),
        task_instructions=journal_suggestion_task_instructions(language),
        user_message=description,
        trusted_backend_data={"available_current_company_accounts": account_data},
    )

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


class GeminiJournalSuggestionProvider(BaseJournalSuggestionProvider):
    """
    Google Gemini-backed journal suggestion provider.

    Falls back to rules provider on any failure.
    """

    def __init__(self) -> None:
        self._fallback = RulesJournalSuggestionProvider()
        self._api_key = getattr(settings, "GEMINI_API_KEY", "").strip()
        self._model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash").strip()
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
            result["source"] = "gemini_fallback_rules"
            result["warnings"] = [
                "Gemini API key is not configured. Backend rules fallback was used."
            ] + result.get("warnings", [])
            return result

        try:
            return self._call_gemini(description, accounts, language)
        except Exception as exc:
            logger.warning(
                "Gemini provider failed, falling back to rules: %s",
                type(exc).__name__,
            )
            result = self._fallback.suggest_journal_entry(
                description=description,
                accounts=accounts,
                language=language,
            )
            result["source"] = "gemini_fallback_rules"
            result["warnings"] = [
                "Gemini suggestion unavailable. Backend rules fallback was used."
            ] + result.get("warnings", [])
            return result

    def _call_gemini(
        self,
        description: str,
        accounts: list[AccountInfo],
        language: str,
    ) -> dict:
        """Make the actual Gemini API call and validate the response."""
        client = genai.Client(api_key=self._api_key)

        prompt = _build_prompt(description, accounts, language)

        response = client.models.generate_content(
            model=self._model,
            contents=prompt.user_message,
            config={
                "system_instruction": prompt.system_instruction,
                "response_mime_type": "application/json",
            },
        )

        raw_content = response.text or ""

        # Strip markdown code fences if the model wrapped the JSON
        content = raw_content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            lines = [
                line for line in lines
                if not line.strip().startswith("```")
            ]
            content = "\n".join(lines).strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(
                "Gemini returned invalid JSON; contract=%s provider=gemini "
                "intent=journal_suggestion outcome=rules_fallback",
                AGENT_CONTRACT_VERSION,
            )
            result = self._fallback.suggest_journal_entry(
                description=description,
                accounts=accounts,
                language=language,
            )
            result["source"] = "gemini_fallback_rules"
            result["warnings"] = [
                "Gemini returned invalid output. Backend rules fallback was used."
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

        logger.info(
            "Accounting agent call contract=%s provider=gemini "
            "intent=journal_suggestion outcome=validated",
            AGENT_CONTRACT_VERSION,
        )

        return {
            "debit_account_id": debit_id,
            "credit_account_id": credit_id,
            "amount": amount,
            "confidence": confidence,
            "explanation": explanation,
            "warnings": warnings,
            "detected_intent": detected_intent,
            "source": "gemini",
        }

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def source_label(self) -> str:
        if self._is_configured:
            return "gemini"
        return "gemini_fallback_rules"

    @property
    def contract_version(self) -> str:
        return AGENT_CONTRACT_VERSION
