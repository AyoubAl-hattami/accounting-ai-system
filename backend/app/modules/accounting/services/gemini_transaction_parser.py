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
from app.modules.accounting.schemas.gemini_assistant_schemas import (
    ConversationTurn,
    ParsedTransaction,
)
from app.modules.accounting.services.account_mapper import ACCOUNT_ALIASES
from app.modules.accounting.services.gemini_agent_contract import (
    AGENT_CONTRACT_VERSION,
    AgentPrompt,
    AgentRuntimeContext,
    build_agent_prompt,
    default_runtime_context,
    transaction_parser_task_instructions,
)

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


MAX_FOLLOWUP_TURNS = 2
MAX_FOLLOWUP_TURN_CHARS = 500
MAX_CONTEXT_TURNS = 8

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _sanitized_turn_content(content: str, limit: int = MAX_FOLLOWUP_TURN_CHARS) -> str:
    return _CONTROL_CHARS.sub(" ", content).strip()[:limit]


def build_followup_message(
    message: str,
    conversation_history: list[ConversationTurn] | None,
) -> str | None:
    """Merge the newest user turns with the current message.

    A follow-up such as "it was 300 from the bank" carries no transaction on its
    own; the subject lives in the preceding turn.  Only user turns are merged —
    assistant replies quote amounts from earlier drafts and would poison the
    amount extraction.
    """
    if not conversation_history:
        return None
    previous = [
        _sanitized_turn_content(turn.content)
        for turn in conversation_history
        if turn.role == "user"
    ]
    previous = [content for content in previous if content][-MAX_FOLLOWUP_TURNS:]
    if not previous:
        return None
    return ". ".join([*previous, _sanitized_turn_content(message)])


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
    runtime_context: AgentRuntimeContext | None = None,
    conversation_history: list[ConversationTurn] | None = None,
) -> AgentPrompt:
    """Build separated contract, account data, and untrusted user content."""
    account_data = [
        {
            "code": account.get("code"),
            "name": account.get("name"),
            "account_type": account.get("account_type"),
            "account_subtype": account.get("account_subtype"),
        }
        for account in accounts_context
        if account.get("is_active", True)
    ]
    history_data = [
        {"role": turn.role, "content": _sanitized_turn_content(turn.content)}
        for turn in (conversation_history or [])[-MAX_CONTEXT_TURNS:]
    ]
    return build_agent_prompt(
        runtime_context=runtime_context
        or default_runtime_context(language=language, provider_name="gemini"),
        task_instructions=transaction_parser_task_instructions(language),
        user_message=message,
        trusted_backend_data={
            "current_company_chart_of_accounts": account_data,
            "bounded_recent_conversation": history_data,
        },
    )

# ── Parser function ───────────────────────────────────────────────────────────

def parse_transaction_message(
    message: str,
    accounts_context: list[dict[str, Any]],
    language: str = "ar",
    runtime_context: AgentRuntimeContext | None = None,
    conversation_history: list[ConversationTurn] | None = None,
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

    prompt = _build_parser_prompt(
        message,
        accounts_context,
        language,
        runtime_context,
        conversation_history,
    )

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt.user_message,
            config={
                "system_instruction": prompt.system_instruction,
                "response_mime_type": "application/json",
            },
        )

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
        logger.info(
            "Accounting agent call contract=%s provider=gemini "
            "intent=transaction_parser outcome=validated",
            AGENT_CONTRACT_VERSION,
        )
        return parsed_transaction

    except json.JSONDecodeError:
        logger.warning(
            "Gemini transaction parser returned invalid JSON; contract=%s "
            "provider=gemini intent=transaction_parser outcome=local_fallback",
            AGENT_CONTRACT_VERSION,
        )
        return local_parse
    except Exception as exc:
        logger.warning(
            "Gemini transaction parser failed safely; contract=%s provider=gemini "
            "intent=transaction_parser outcome=local_fallback error_type=%s",
            AGENT_CONTRACT_VERSION,
            type(exc).__name__,
        )
        return local_parse
