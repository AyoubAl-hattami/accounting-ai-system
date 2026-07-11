"""
Gemini-powered semantic transaction parser.

Converts natural language (Arabic, English, dialect, mixed) into a structured
ParsedTransaction object.  Gemini returns HINTS only — never account IDs.
Backend maps hints to real accounts deterministically.

Falls back to deterministic local parsing when Gemini is unavailable, then to
the legacy rules engine only when the message cannot be parsed safely.
"""

import json
import logging
import re
from typing import Any

from app.core.config import settings
from app.modules.accounting.schemas.gemini_assistant_schemas import ParsedTransaction
from app.modules.accounting.services.account_mapper import ACCOUNT_ALIASES

logger = logging.getLogger(__name__)
# -- Deterministic local parser fallback ---------------------------------------

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_AMOUNT_PATTERN = re.compile(r"\d[\d,]*(?:\.\d+)?")
_LOCAL_FIRST_MIN_CONFIDENCE = 0.65
_GEMINI_WEAK_CONFIDENCE = 0.55

_PAYMENT_VERBS = [
    "تم دفع", "دفعنا", "دفعت", "دفع", "سددت", "سددنا", "سداد", "خرجنا", "خرج",
    "paid", "pay", "settled",
]
_RECEIPT_VERBS = [
    "تم استلام", "استلمنا", "استلمت", "وصلنا", "قبضنا", "تحصيل", "حصلنا",
    "received", "collected", "got paid",
]
_TRANSFER_VERBS = ["حولت", "حولنا", "تحويل", "نقلت", "نقلنا", "transfer", "transferred"]
_ASSET_PURCHASE_VERBS = ["اشتريت", "اشترينا", "شراء", "bought", "purchased"]

_EXPENSE_CATEGORY_HINTS = {
    "utilities": "utilities expense",
    "rent": "rent expense",
    "salary": "salary expense",
    "supplies": "supplies expense",
    "software": "software expense",
    "transportation": "transportation expense",
    "food": "meals expense",
}


def _normalize_message(message: str) -> str:
    """Normalize only what is needed for deterministic parsing."""
    return message.translate(_ARABIC_DIGITS).lower().replace("٫", ".").replace("٬", ",")


def _extract_amount(message: str) -> float | None:
    match = _AMOUNT_PATTERN.search(_normalize_message(message))
    if not match:
        return None
    value = match.group(0).replace(",", "")
    try:
        amount = float(value)
    except ValueError:
        return None
    return amount if amount > 0 else None


def _has_any(text: str, phrases: list[str]) -> bool:
    return any(phrase.lower() in text for phrase in phrases)


def _matches_category(text: str, category: str) -> bool:
    return any(alias.lower() in text for alias in ACCOUNT_ALIASES.get(category, []))


def _first_category(text: str, categories: list[str]) -> str | None:
    for category in categories:
        if _matches_category(text, category):
            return category
    return None


def _infer_bank_cash(text: str) -> str:
    has_bank = _matches_category(text, "bank")
    has_cash = _matches_category(text, "cash")
    if has_bank and not has_cash:
        return "bank"
    if has_cash and not has_bank:
        return "cash"
    return "unknown"


def _first_alias_position(text: str, category: str) -> int | None:
    positions = [
        text.find(alias.lower())
        for alias in ACCOUNT_ALIASES.get(category, [])
        if alias.lower() in text
    ]
    return min(positions) if positions else None


def _infer_transfer_direction(text: str) -> tuple[str | None, str | None]:
    bank_pos = _first_alias_position(text, "bank")
    cash_pos = _first_alias_position(text, "cash")
    if bank_pos is None or cash_pos is None or bank_pos == cash_pos:
        return None, None
    if bank_pos < cash_pos:
        return "bank", "cash"
    return "cash", "bank"


def _parse_transaction_locally(message: str, language: str) -> ParsedTransaction | None:
    """Parse simple high-confidence accounting phrases without calling Gemini."""
    text = _normalize_message(message)
    amount = _extract_amount(message)
    if amount is None:
        return None

    payment_source = _infer_bank_cash(text)
    expense_category = _first_category(text, list(_EXPENSE_CATEGORY_HINTS.keys()))

    if _has_any(text, _TRANSFER_VERBS) and _matches_category(text, "bank") and _matches_category(text, "cash"):
        source, destination = _infer_transfer_direction(text)
        if source and destination:
            return ParsedTransaction(
                intent="create_journal_entry",
                transaction_type="bank_cash_transfer",
                amount=amount,
                description=message.strip(),
                payment_source_hint=source,
                receiving_account_hint=destination,
                confidence=0.85,
                needs_clarification=False,
            )

    if _has_any(text, _PAYMENT_VERBS) or expense_category:
        if _matches_category(text, "accounts_payable"):
            return ParsedTransaction(
                intent="create_journal_entry",
                transaction_type="supplier_payment",
                amount=amount,
                description=message.strip(),
                debit_account_hint="accounts payable",
                payment_source_hint=payment_source,
                confidence=0.78,
                needs_clarification=False,
            )

        if _has_any(text, _ASSET_PURCHASE_VERBS) and _matches_category(text, "equipment"):
            return ParsedTransaction(
                intent="create_journal_entry",
                transaction_type="asset_purchase",
                amount=amount,
                description=message.strip(),
                debit_account_hint="equipment",
                income_or_expense_nature="equipment",
                payment_source_hint=payment_source,
                confidence=0.75,
                needs_clarification=False,
            )

        nature = expense_category or "expense"
        debit_hint = _EXPENSE_CATEGORY_HINTS.get(nature, "expense")
        return ParsedTransaction(
            intent="create_journal_entry",
            transaction_type="expense_payment",
            amount=amount,
            description=message.strip(),
            debit_account_hint=debit_hint,
            income_or_expense_nature=nature,
            payment_source_hint=payment_source,
            confidence=0.8 if expense_category else 0.65,
            needs_clarification=False,
        )

    if _has_any(text, _RECEIPT_VERBS) or _matches_category(text, "sales"):
        receiving_account = _infer_bank_cash(text)
        if _matches_category(text, "accounts_receivable"):
            return ParsedTransaction(
                intent="create_journal_entry",
                transaction_type="customer_receipt",
                amount=amount,
                description=message.strip(),
                credit_account_hint="accounts receivable",
                receiving_account_hint=receiving_account,
                confidence=0.72,
                needs_clarification=False,
            )
        return ParsedTransaction(
            intent="create_journal_entry",
            transaction_type="income_receipt",
            amount=amount,
            description=message.strip(),
            credit_account_hint="sales revenue",
            receiving_account_hint=receiving_account,
            confidence=0.68,
            needs_clarification=False,
        )

    return None


def _is_reasonable_local_parse(parsed: ParsedTransaction | None) -> bool:
    return (
        parsed is not None
        and parsed.intent == "create_journal_entry"
        and parsed.transaction_type != "unknown"
        and parsed.amount is not None
        and parsed.confidence >= _LOCAL_FIRST_MIN_CONFIDENCE
    )


def looks_like_accounting_message_with_amount(message: str) -> bool:
    """Return True when text has an amount plus transaction-like wording."""
    text = _normalize_message(message)
    if _extract_amount(message) is None:
        return False

    verbs = _PAYMENT_VERBS + _RECEIPT_VERBS + _TRANSFER_VERBS + _ASSET_PURCHASE_VERBS
    if _has_any(text, verbs):
        return True

    return any(_matches_category(text, category) for category in ACCOUNT_ALIASES)


def _is_generic_clarification(parsed: ParsedTransaction) -> bool:
    question = (parsed.clarification_question or "").strip().lower()
    if not question and not parsed.clarification_options:
        return True

    specific_terms = (
        "bank", "cash", "customer", "supplier", "expense", "revenue",
        "البنك", "الصندوق", "عميل", "زبون", "مورد", "مصروف", "إيراد", "ايراد",
    )
    if any(term in question for term in specific_terms):
        return False

    generic_terms = (
        "لم أفهم", "لا أفهم", "يمكنني مساعدتك", "وضح", "توضيح", "مزيد من",
        "how can i help", "what can i help", "please clarify", "more details",
        "not sure", "do not understand", "don't understand",
    )
    return any(term in question for term in generic_terms)


def _should_try_local_fallback(parsed: ParsedTransaction, message: str) -> bool:
    message_has_amount = _extract_amount(message) is not None
    accounting_like = looks_like_accounting_message_with_amount(message)

    return (
        parsed.intent == "not_accounting"
        or parsed.transaction_type == "unknown"
        or (message_has_amount and parsed.amount is None)
        or (accounting_like and parsed.confidence < _GEMINI_WEAK_CONFIDENCE)
        or (accounting_like and parsed.intent == "clarification" and _is_generic_clarification(parsed))
    )


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_parser_prompt(
    message: str,
    accounts_context: list[dict[str, Any]],
    language: str,
) -> str:
    """Build the Gemini prompt for semantic transaction extraction."""

    lang_instruction = (
        "Return the description and clarification_question in Arabic."
        if language == "ar"
        else "Return the description and clarification_question in English."
    )

    # Build chart of accounts summary for Gemini context
    accounts_text = "\n".join(
        f"  - Code: {a['code']}, Name: {a['name']}, Type: {a['account_type']}"
        for a in accounts_context
        if a.get("is_active", True)
    )

    return f"""You are an expert accounting transaction parser.

TASK: Parse the user's natural language message into a structured JSON transaction.
The user may write in Arabic, Arabic dialect, English, or a mix.

RULES:
1. Return ONLY valid JSON, no markdown, no code fences, no extra text.
2. You must NOT invent or return account IDs. Return text HINTS only.
3. "debit_account_hint" and "credit_account_hint" should be descriptive text
   (e.g. "utilities expense", "bank", "cash", "sales revenue", "accounts payable").
4. If you cannot determine the payment source (bank vs cash), set
   needs_clarification=true and ask specifically.
5. If you cannot determine whether a receipt is new revenue vs collection
   from a customer, set needs_clarification=true and ask specifically.
6. "amount" must be a positive number extracted from the message, or null.
7. "confidence" is 0.0-1.0 based on how certain you are.
8. "income_or_expense_nature" should be a category like: electricity, rent,
   salary, supplies, sales, services, equipment, etc.
9. {lang_instruction}
10. Common Arabic dialect phrases:
    - "دفعت" / "دفعنا" / "خرجنا" = paid / expense
    - "كهربا" / "كهرباء" = electricity
    - "استلمنا" / "وصلنا" / "قبضنا" = received
    - "تاجر" / "مورد" = supplier/trader
    - "عميل" / "زبون" = customer/client
    - "حولت" / "نقلت" = transferred
    - "البنك" = bank, "الصندوق" = cash box
    - "حق" = for (dialect), e.g. "حق الكهرباء" = for electricity

TRANSACTION TYPES:
- "expense_payment": paying for an expense (rent, electricity, supplies, etc.)
- "income_receipt": receiving income/revenue
- "supplier_payment": paying a supplier / accounts payable
- "customer_receipt": collecting from a customer / accounts receivable
- "bank_cash_transfer": transferring between bank and cash
- "asset_purchase": buying equipment/assets
- "liability_payment": paying off a loan/liability
- "unknown": cannot determine

JSON SCHEMA:
{{
  "intent": "create_journal_entry" | "clarification" | "not_accounting",
  "transaction_type": "<type from list above>",
  "amount": <number or null>,
  "description": "<clean accounting description>",
  "debit_account_hint": "<text hint or null>",
  "credit_account_hint": "<text hint or null>",
  "income_or_expense_nature": "<category or null>",
  "counterparty": "<name or null>",
  "payment_source_hint": "bank" | "cash" | "unknown" | null,
  "receiving_account_hint": "bank" | "cash" | "unknown" | null,
  "confidence": <0.0-1.0>,
  "needs_clarification": <boolean>,
  "clarification_question": "<specific question or null>",
  "clarification_options": ["option1", "option2"]
}}

COMPANY CHART OF ACCOUNTS:
{accounts_text}

USER MESSAGE: "{message}"

Parse this message into the JSON schema above. Return JSON only."""


# ── Parser function ───────────────────────────────────────────────────────────

def parse_transaction_message(
    message: str,
    accounts_context: list[dict[str, Any]],
    language: str = "ar",
) -> ParsedTransaction | None:
    """
    Use Gemini to semantically parse a user message into a structured transaction.

    Returns ParsedTransaction on success, a deterministic local parse when Gemini
    is unavailable or unusable, and None only when both parsers fail.
    """
    local_parse = _parse_transaction_locally(message, language)
    if _is_reasonable_local_parse(local_parse):
        return local_parse

    api_key = getattr(settings, "GEMINI_API_KEY", "").strip()
    model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash").strip()

    if not api_key:
        return local_parse

    prompt = _build_parser_prompt(message, accounts_context, language)

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=prompt)

        raw_content = (response.text or "").strip()

        # Strip markdown code fences if the model wrapped the JSON
        content = raw_content
        if content.startswith("```"):
            lines = content.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            content = "\n".join(lines).strip()

        parsed = json.loads(content)

        # Validate with Pydantic
        parsed_transaction = ParsedTransaction(**parsed)
        if _should_try_local_fallback(parsed_transaction, message) and local_parse is not None:
            return local_parse
        return parsed_transaction

    except json.JSONDecodeError as exc:
        logger.warning("Gemini transaction parser returned invalid JSON: %s", exc)
        return local_parse
    except Exception as exc:
        logger.warning(
            "Gemini transaction parser failed: %s: %s",
            type(exc).__name__, exc,
        )
        return local_parse
