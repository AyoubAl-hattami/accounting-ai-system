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
from app.modules.accounting.schemas.ai_suggestion_schemas import AccountInfo
from app.modules.accounting.services.ai_providers.base import (
    BaseJournalSuggestionProvider,
)
from app.modules.accounting.services.ai_providers.rules_provider import (
    RulesJournalSuggestionProvider,
)

logger = logging.getLogger(__name__)


def _build_prompt(
    description: str,
    accounts: list[AccountInfo],
    language: str,
) -> str:
    """Build a single prompt for Gemini with system instructions and user data."""
    lang_instruction = (
        "Respond with the explanation field in Arabic."
        if language == "ar"
        else "Respond with the explanation field in English."
    )

    accounts_text = "\n".join(
        f"  - ID: {a.id}, Code: {a.code}, Name: {a.name}, Type: {a.account_type}"
        for a in accounts
        if a.is_active
    )

    return f"""You are an expert accounting assistant that suggests double-entry journal entries.

Rules:
1. Return ONLY valid JSON, no markdown, no code fences, no extra text.
2. Use ONLY account IDs from the provided accounts list. Never invent account IDs.
3. If you are unsure about which account to use, set the account ID to null and include a warning.
4. The amount must be a positive number or null if not detectable.
5. Use proper double-entry accounting logic (debits increase assets/expenses, credits increase liabilities/equity/income).
6. {lang_instruction}
7. Do not create, post, or save any journal entry. Only suggest.

Your JSON response must have exactly this shape:
{{
  "debit_account_id": <int or null>,
  "credit_account_id": <int or null>,
  "amount": <positive float or null>,
  "confidence": "high" | "medium" | "low",
  "explanation": "<accounting explanation string>",
  "warnings": ["<optional warning strings>"],
  "detected_intent": "<intent like rent_lease, salary_payroll, sales_revenue, owner_investment, loan_payment, loan_received, purchase_equipment, or unknown>"
}}

Transaction description: "{description}"

Available accounts:
{accounts_text}

Suggest a journal entry for this transaction. Return JSON only."""


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
            contents=prompt,
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
            logger.warning("Gemini returned invalid JSON, falling back to rules")
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
