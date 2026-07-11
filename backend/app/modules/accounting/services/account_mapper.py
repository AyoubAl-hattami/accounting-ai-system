"""
Deterministic account mapper.

Maps ParsedTransaction hints (text descriptions) to real company accounts
using name matching, aliases, and account type inference.

Never invents accounts — returns clarification when ambiguous.
"""

from __future__ import annotations

import logging
from typing import Any

from app.modules.accounting.schemas.gemini_assistant_schemas import (
    MappedTransaction,
    ParsedTransaction,
)

logger = logging.getLogger(__name__)


# ── Account aliases ───────────────────────────────────────────────────────────
# Key = canonical category name.
# Values = Arabic + English aliases (lowercase for matching).
# Extensible to DB later — users can add custom aliases per account.

ACCOUNT_ALIASES: dict[str, list[str]] = {
    "utilities": [
        "كهرباء", "كهربا", "ماء", "مياه", "إنترنت", "انترنت",
        "خدمات", "هاتف", "تلفون", "اتصالات", "غاز",
        "electricity", "water", "internet", "utility", "utilities",
        "phone", "telecom", "gas",
    ],
    "rent": [
        "إيجار", "ايجار", "أجرة", "اجرة",
        "rent", "lease", "rental",
    ],
    "salary": [
        "رواتب", "راتب", "أجور", "اجور", "مكافأة", "مكافأت",
        "salary", "salaries", "wages", "payroll", "bonus",
    ],
    "supplies": [
        "مستلزمات", "قرطاسية", "أدوات", "ادوات",
        "supplies", "stationery", "office supplies",
    ],
    "bank": [
        "بنك", "البنك", "مصرف", "المصرف",
        "bank", "main bank",
    ],
    "cash": [
        "صندوق", "الصندوق", "نقد", "نقدية", "كاش",
        "cash", "petty cash", "cash box",
    ],
    "sales": [
        "مبيعات", "إيراد", "ايراد", "إيرادات", "ايرادات",
        "revenue", "sales", "sales revenue", "income",
    ],
    "accounts_receivable": [
        "ذمم مدينة", "عملاء", "مدينون", "زبائن",
        "accounts receivable", "receivable", "receivables", "debtors", "customers",
    ],
    "accounts_payable": [
        "ذمم دائنة", "موردين", "مورد", "دائنون", "تاجر",
        "accounts payable", "payable", "payables", "creditors", "supplier",
    ],
    "equipment": [
        "معدات", "أجهزة", "اجهزة", "أثاث", "اثاث", "آلات", "الات",
        "equipment", "machinery", "furniture", "devices",
    ],
    "software": [
        "برمجيات", "برنامج", "اشتراك",
        "software", "subscription",
    ],
    "transportation": [
        "نقل", "مواصلات", "بنزين", "وقود", "سيارة",
        "transport", "transportation", "fuel", "gas", "vehicle",
    ],
    "food": [
        "أكل", "اكل", "طعام", "مطعم", "وجبات", "ضيافة",
        "food", "meals", "catering", "hospitality",
    ],
    "owner_equity": [
        "رأس مال", "رأسمال", "حقوق ملكية",
        "capital", "owner capital", "equity", "owner equity",
    ],
}


def _normalize(text: str) -> str:
    """Lowercase and strip for matching."""
    return text.strip().lower()


def _alias_match(hint: str, category: str) -> bool:
    """Check if a hint matches any alias in a category."""
    hint_lower = _normalize(hint)
    aliases = ACCOUNT_ALIASES.get(category, [])
    return any(alias in hint_lower or hint_lower in alias for alias in aliases)


def _find_alias_category(hint: str) -> str | None:
    """Find the alias category that best matches a hint."""
    hint_lower = _normalize(hint)
    for category, aliases in ACCOUNT_ALIASES.items():
        for alias in aliases:
            if alias in hint_lower or hint_lower in alias:
                return category
    return None


_GENERIC_TYPE_WORDS = {
    "asset", "assets", "liability", "liabilities", "equity",
    "income", "revenue", "expense", "expenses",
}

_GENERIC_TYPE_NAMES = {
    "asset": {"asset", "assets"},
    "liability": {"liability", "liabilities"},
    "equity": {"equity"},
    "income": {"income", "revenue", "revenues"},
    "expense": {"expense", "expenses"},
}


def _score_account(
    account: dict[str, Any],
    hint: str,
    alias_category: str | None,
    required_type: str | None = None,
) -> float:
    """
    Score how well an account matches a hint + alias category.
    Higher = better match.  Returns 0.0 if type mismatch.
    """
    account_type = account.get("account_type")
    if required_type and account_type != required_type:
        return 0.0

    name_lower = _normalize(account.get("name", ""))
    hint_lower = _normalize(hint)
    score = 0.0
    generic_names = _GENERIC_TYPE_NAMES.get(required_type or account_type or "", set())
    is_generic_hint = hint_lower in _GENERIC_TYPE_WORDS

    # Generic type hints should prefer the parent type account, not an unrelated
    # specific account such as Rent Expense for a missing Utilities Expense.
    if is_generic_hint:
        if name_lower in generic_names:
            score += 10.0
        elif required_type and account_type == required_type:
            score += 1.0
    elif hint_lower in name_lower or name_lower in hint_lower:
        score += 10.0

    # Alias category match
    if alias_category:
        category_aliases = ACCOUNT_ALIASES.get(alias_category, [])
        for alias in category_aliases:
            if alias in name_lower:
                score += 8.0
                break

    # Partial word overlap, ignoring generic accounting type words.
    hint_words = set(hint_lower.split()) - _GENERIC_TYPE_WORDS
    name_words = set(name_lower.split()) - _GENERIC_TYPE_WORDS
    overlap = hint_words & name_words
    if overlap:
        score += len(overlap) * 2.0

    # Penalize top-level parent accounts unless they are the requested generic type.
    code = account.get("code", "")
    if (code.endswith("000") or code.endswith("00")) and name_lower not in generic_names:
        score -= 1.0

    return score


def _find_best_account(
    accounts: list[dict[str, Any]],
    hint: str | None,
    required_type: str | None = None,
    exclude_ids: set[int] | None = None,
) -> dict[str, Any] | None:
    """Find the best matching account for a hint."""
    if not hint:
        return None

    exclude = exclude_ids or set()
    alias_category = _find_alias_category(hint)

    scored: list[tuple[float, dict[str, Any]]] = []
    for acct in accounts:
        if not acct.get("is_active", True):
            continue
        if acct["id"] in exclude:
            continue
        s = _score_account(acct, hint, alias_category, required_type)
        if s > 0:
            scored.append((s, acct))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def _find_bank_or_cash(
    accounts: list[dict[str, Any]],
    preference: str | None = None,
) -> dict[str, Any] | None:
    """Find bank or cash account by preference."""
    if preference == "bank":
        return _find_best_account(accounts, "bank", required_type="asset")
    if preference == "cash":
        return _find_best_account(accounts, "cash", required_type="asset")

    # No explicit preference: choose the most common default order.
    result = _find_best_account(accounts, "bank", required_type="asset")
    if result:
        return result
    return _find_best_account(accounts, "cash", required_type="asset")


# ── Main mapper ───────────────────────────────────────────────────────────────

def map_to_accounts(
    parsed: ParsedTransaction,
    accounts: list[dict[str, Any]],
    language: str = "ar",
) -> MappedTransaction:
    """
    Map ParsedTransaction hints to real company accounts.

    Returns MappedTransaction with resolved account IDs, or
    needs_clarification=True if the mapper can't resolve confidently.
    """
    warnings: list[str] = []
    debit_acct = None
    credit_acct = None
    needs_clarification = parsed.needs_clarification
    clarification_question = parsed.clarification_question
    clarification_options = list(parsed.clarification_options)

    tx_type = parsed.transaction_type

    # ── Expense payment: Debit=expense, Credit=bank/cash ──────────────────
    if tx_type == "expense_payment":
        # Find expense account by nature hint
        if parsed.debit_account_hint:
            debit_acct = _find_best_account(
                accounts, parsed.debit_account_hint, required_type="expense",
            )
        if not debit_acct and parsed.income_or_expense_nature:
            debit_acct = _find_best_account(
                accounts, parsed.income_or_expense_nature, required_type="expense",
            )

        if not debit_acct:
            # Try generic expense
            debit_acct = _find_best_account(accounts, "expense", required_type="expense")

        if not debit_acct:
            nature = parsed.income_or_expense_nature or parsed.debit_account_hint or "expense"
            warnings.append(
                f"لم أجد حساب مصروف مناسب لـ '{nature}'."
                if language == "ar"
                else f"No suitable expense account found for '{nature}'."
            )

        # Find credit (bank/cash)
        source = parsed.payment_source_hint
        if source and source != "unknown":
            credit_acct = _find_bank_or_cash(accounts, preference=source)
        elif not needs_clarification:
            # Ask which payment source
            needs_clarification = True
            clarification_question = (
                f"هل تم دفع {_fmt_amount(parsed.amount)} من البنك أم الصندوق؟"
                if language == "ar"
                else f"Was {_fmt_amount(parsed.amount)} paid from bank or cash?"
            )
            clarification_options = (
                ["البنك", "الصندوق"]
                if language == "ar"
                else ["Bank", "Cash"]
            )

    # ── Income receipt: Debit=bank/cash, Credit=revenue ───────────────────
    elif tx_type == "income_receipt":
        # Find revenue account
        if parsed.credit_account_hint:
            credit_acct = _find_best_account(
                accounts, parsed.credit_account_hint, required_type="income",
            )
        if not credit_acct:
            credit_acct = _find_best_account(
                accounts, "sales revenue", required_type="income",
            )
        if not credit_acct:
            credit_acct = _find_best_account(accounts, "income", required_type="income")

        # Find debit (bank/cash)
        dest = parsed.receiving_account_hint
        if dest and dest != "unknown":
            debit_acct = _find_bank_or_cash(accounts, preference=dest)
        elif not needs_clarification:
            needs_clarification = True
            clarification_question = (
                f"هل تم استلام {_fmt_amount(parsed.amount)} في البنك أم الصندوق؟"
                if language == "ar"
                else f"Was {_fmt_amount(parsed.amount)} received in bank or cash?"
            )
            clarification_options = (
                ["البنك", "الصندوق"]
                if language == "ar"
                else ["Bank", "Cash"]
            )

    # ── Customer receipt: Debit=bank/cash, Credit=receivable ──────────────
    elif tx_type == "customer_receipt":
        credit_acct = _find_best_account(
            accounts, "accounts receivable", required_type="asset",
        )
        dest = parsed.receiving_account_hint
        if dest and dest != "unknown":
            debit_acct = _find_bank_or_cash(accounts, preference=dest)
        elif not needs_clarification:
            needs_clarification = True
            clarification_question = (
                f"هل تم تحصيل {_fmt_amount(parsed.amount)} في البنك أم الصندوق؟"
                if language == "ar"
                else f"Was {_fmt_amount(parsed.amount)} collected in bank or cash?"
            )
            clarification_options = (
                ["البنك", "الصندوق"]
                if language == "ar"
                else ["Bank", "Cash"]
            )

    # ── Supplier payment: Debit=payable, Credit=bank/cash ─────────────────
    elif tx_type == "supplier_payment":
        debit_acct = _find_best_account(
            accounts, "accounts payable", required_type="liability",
        )
        source = parsed.payment_source_hint
        if source and source != "unknown":
            credit_acct = _find_bank_or_cash(accounts, preference=source)
        elif not needs_clarification:
            needs_clarification = True
            clarification_question = (
                f"هل تم سداد {_fmt_amount(parsed.amount)} للمورد من البنك أم الصندوق؟"
                if language == "ar"
                else f"Was {_fmt_amount(parsed.amount)} paid to supplier from bank or cash?"
            )
            clarification_options = (
                ["البنك", "الصندوق"]
                if language == "ar"
                else ["Bank", "Cash"]
            )

    # ── Bank ↔ Cash transfer: Debit=destination, Credit=source ────────────
    elif tx_type == "bank_cash_transfer":
        source = parsed.payment_source_hint
        dest = parsed.receiving_account_hint
        if source and source != "unknown":
            credit_acct = _find_bank_or_cash(accounts, preference=source)
        if dest and dest != "unknown":
            debit_acct = _find_bank_or_cash(
                accounts, preference=dest,
            )
        # Ensure debit ≠ credit
        if debit_acct and credit_acct and debit_acct["id"] == credit_acct["id"]:
            # Try to find the other one
            if dest == "cash":
                debit_acct = _find_best_account(accounts, "cash", required_type="asset")
            elif dest == "bank":
                debit_acct = _find_best_account(accounts, "bank", required_type="asset")

    # ── Asset purchase: Debit=asset/expense, Credit=bank/cash ─────────────
    elif tx_type == "asset_purchase":
        if parsed.debit_account_hint:
            debit_acct = _find_best_account(
                accounts, parsed.debit_account_hint, required_type="asset",
            )
        if not debit_acct and parsed.income_or_expense_nature:
            debit_acct = _find_best_account(
                accounts, parsed.income_or_expense_nature, required_type="asset",
            )
        if not debit_acct:
            # Try expense fallback
            debit_acct = _find_best_account(
                accounts, parsed.debit_account_hint or "equipment", required_type="expense",
            )
        source = parsed.payment_source_hint
        if source and source != "unknown":
            credit_acct = _find_bank_or_cash(accounts, preference=source)
        else:
            credit_acct = _find_bank_or_cash(accounts)

    # ── Liability payment: Debit=liability, Credit=bank/cash ──────────────
    elif tx_type == "liability_payment":
        if parsed.debit_account_hint:
            debit_acct = _find_best_account(
                accounts, parsed.debit_account_hint, required_type="liability",
            )
        source = parsed.payment_source_hint
        if source and source != "unknown":
            credit_acct = _find_bank_or_cash(accounts, preference=source)
        else:
            credit_acct = _find_bank_or_cash(accounts)

    # ── Unknown type ──────────────────────────────────────────────────────
    else:
        # Try generic hint-based matching
        if parsed.debit_account_hint:
            debit_acct = _find_best_account(accounts, parsed.debit_account_hint)
        if parsed.credit_account_hint:
            credit_acct = _find_best_account(accounts, parsed.credit_account_hint)

    return MappedTransaction(
        debit_account_id=debit_acct["id"] if debit_acct else None,
        debit_account_name=debit_acct["name"] if debit_acct else None,
        debit_account_code=debit_acct["code"] if debit_acct else None,
        credit_account_id=credit_acct["id"] if credit_acct else None,
        credit_account_name=credit_acct["name"] if credit_acct else None,
        credit_account_code=credit_acct["code"] if credit_acct else None,
        amount=parsed.amount,
        description=parsed.description or "",
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
        clarification_options=clarification_options,
        warnings=warnings,
    )


def _fmt_amount(amount: float | None) -> str:
    """Format amount for display, or return placeholder."""
    if amount is None:
        return "المبلغ"
    return f"{amount:,.2f}"
