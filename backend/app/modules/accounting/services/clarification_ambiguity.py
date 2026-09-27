"""Decide whether a clarification reply is safe to resolve by pattern.

WHAT THIS IS FOR
----------------
When the assistant asks "bank or cash?", the reply used to go straight into
``_resolve_bank_cash_answer``, which scans for bank terms and then for cash
terms and returns the first hit. That has no notion of negation and no notion
of what accounts exist, so two whole classes of reply resolved to the wrong
account **silently** -- a value came back, so the "I did not understand"
branch never fired and a draft was offered against an account the user had
just ruled out. Both are measured in RAG-19:

    "لا، من الصندوق مش من البنك"   (not the bank, from the cash box)  -> bank
    "محفظة ون كاش"                 (the OneCash wallet, account 1130) -> 1100

This module does not resolve anything. It answers one question -- *is this
reply unambiguous enough to hand to a pattern?* -- and everything it is
unsure about is escalated.

THE ASYMMETRY IS THE WHOLE SAFETY ARGUMENT
------------------------------------------
This detector is allowed to be crude. It is not allowed to be confident.

A false escalation costs one round trip once the interpretation step exists,
and until then costs the user a re-ask. A false pass costs a journal entry
against the wrong account, which is the bug this exists to prevent. So every
rule below is written to escalate on doubt, and the word lists only need to
be over-inclusive, never precise.

WHY IT READS THE CHART AND NOT A LIST
-------------------------------------
``كاش`` is unambiguous as a word and ambiguous the moment the chart contains
``محفظة ون كاش``. A detector that decided from a fixed vocabulary would keep
making exactly the error it exists to catch, so the caller passes this
company's live accounts and the collision test runs against them.

The test is not "does the reply name an account" -- ``الصندوق`` names account
1100 and is also the cash concept, and those agree, so it stays instant. It
is "does the account the reply names DISAGREE with the concept the pattern
would pick", compared on ``account_subtype``. ``الصندوق`` is subtype ``cash``
and the concept is cash: consistent. ``محفظة ون كاش`` is subtype ``e_wallet``
and the concept is cash: not consistent, escalate.

WHERE THE VOCABULARY LIVES
--------------------------
Here, not in the service, and the service imports it back under the same
names. A second copy would not be caught by any test -- the detector and the
resolver would simply drift, and the detector would start passing replies the
resolver reads differently, which is the failure mode this whole module is
about. One definition removes the question. Same reasoning as the ``_CAN_*``
permission sets in ``assistant_handler_registry``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

# ── The shared vocabulary ────────────────────────────────────────────────────
# Imported back into gemini_assistant_service under these names, so the
# resolvers and this detector are reading one list and not two.

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

OPTION_FIRST = frozenset({"1", "اول", "الأول", "الاول", "واحد"})
OPTION_SECOND = frozenset({"2", "ثاني", "الثاني", "اتنين", "اثنين"})

BANK_TERMS = ("البنك", "بنك", "مصرف", "bank")
CASH_TERMS = ("الصندوق", "صندوق", "كاش", "نقد", "نقدية", "cash")

SUPPLIER_TERMS = ("سداد مورد", "مورد", "supplier", "payable")
EXPENSE_TERMS = ("مصروف جديد", "مصروف", "expense")
CUSTOMER_TERMS = ("تحصيل من عميل", "عميل", "زبون", "customer", "receivable")
INCOME_TERMS = ("إيراد جديد", "ايراد جديد", "إيراد", "ايراد", "revenue", "income")

# Presence of any of these is SUFFICIENT to escalate. The list is deliberately
# over-inclusive: "actually cash" is not a negation and escalating it costs a
# round trip, while missing "مش" costs a wrong ledger entry. It is not a
# grammar -- a reply that merely mentions one of these is treated as a reply
# whose polarity a substring scan cannot be trusted to read.
#
# MATCHED AS WHOLE TOKENS, NOT SUBSTRINGS, and that distinction is not
# cosmetic. Arabic negation particles are two letters and they live inside
# ordinary words: مو is inside مورد (supplier), and لا is inside خلاص. A
# substring scan here escalates every supplier answer ever given -- measured,
# which is how this list came to be split.
#
# Over-escalating is the safe direction for a REPLY, but not for the detector
# itself: a rule that fires on everything is a rule that has stopped
# discriminating, and the instant path would quietly die.
NEGATION_TOKENS = frozenset({
    "لا", "مش", "ليس", "بدل", "غير", "مو", "ما", "ماهو",
    "not", "no", "nope", "instead", "rather", "actually", "wrong",
})

# Matched by containment, for forms that cannot appear inside an unrelated
# word. "n't" is a suffix of a contraction and never a token of its own.
NEGATION_SUBSTRINGS = ("n't",)

# Token boundaries. Arabic and Latin punctuation both, because "لا، من البنك"
# separates on an Arabic comma and "no, bank" on a Latin one.
_TOKEN_SEPARATORS = " \t\n\r،؛,.;:!?()[]{}\"'«»/\\|-—–"

# What each concept means in chart terms, so a named account can be compared
# with the concept a pattern would have chosen.
_CONCEPT_SUBTYPES = {"bank": {"bank"}, "cash": {"cash"}}

# A reply shorter than this is not matched against account names by
# containment. "بنك" inside "بنك الكريمي" is a real signal; a one or two
# character fragment inside a long account name is noise.
_MIN_ACCOUNT_FRAGMENT = 3


@dataclass(frozen=True, slots=True)
class ClarificationAmbiguity:
    """Whether a pattern may read this reply, and if not, why not.

    ``reason`` is not for the user. It names which rule escalated, so that a
    test can assert the detector escalated for the reason it was supposed to
    and not by accident, and so that a log line says something useful.
    """

    unambiguous: bool
    reason: str | None = None
    matched_accounts: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return self.unambiguous


def normalize(message: str) -> str:
    """The one normalisation both the detector and the resolvers use."""
    return message.translate(ARABIC_DIGITS).strip().lower()


def _tokens(text: str) -> set[str]:
    """Split on whitespace and punctuation, in both scripts."""
    table = str.maketrans({character: " " for character in _TOKEN_SEPARATORS})
    return {token for token in text.translate(table).split() if token}


def _negated(text: str) -> bool:
    if any(fragment in text for fragment in NEGATION_SUBSTRINGS):
        return True
    return bool(_tokens(text) & NEGATION_TOKENS)


def _concepts_present(text: str, missing_fields: Sequence[str]) -> set[str]:
    """Which candidate answers this reply could be, for the question asked.

    Keyed on the missing field, because "bank or cash" and "supplier or
    expense" are different questions with different candidate sets, and a
    reply mentioning one concept from each is ambiguous about neither.
    """
    found: set[str] = set()
    wants_source = {"payment_source", "receiving_account"} & set(missing_fields)
    wants_type = {
        "transaction_type", "supplier_or_expense", "customer_or_income",
    } & set(missing_fields)

    if wants_source:
        if any(term in text for term in BANK_TERMS):
            found.add("bank")
        if any(term in text for term in CASH_TERMS):
            found.add("cash")
    if wants_type:
        if any(term in text for term in SUPPLIER_TERMS):
            found.add("supplier")
        if any(term in text for term in EXPENSE_TERMS):
            found.add("expense")
        if any(term in text for term in CUSTOMER_TERMS):
            found.add("customer")
        if any(term in text for term in INCOME_TERMS):
            found.add("income")
    return found


def _named_accounts(
    text: str, accounts: Sequence[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    """Accounts from THIS company that the reply appears to name.

    Matched both ways round. The reply may contain the account name
    ("من محفظة جيب" contains "محفظة جيب"), or the account name may contain the
    reply ("ون كاش" is inside "محفظة ون كاش") -- users name accounts by the
    part they remember.
    """
    hits: list[Mapping[str, Any]] = []
    for account in accounts:
        if not account.get("is_active", True):
            continue
        name = str(account.get("name") or "").strip().lower()
        code = str(account.get("code") or "").strip().lower()
        if code and code in text:
            hits.append(account)
            continue
        if not name:
            continue
        if name in text:
            hits.append(account)
        elif len(text) >= _MIN_ACCOUNT_FRAGMENT and text in name:
            hits.append(account)
    return hits


def clarification_ambiguity(
    answer: str,
    accounts: Sequence[Mapping[str, Any]],
    missing_fields: Sequence[str],
) -> ClarificationAmbiguity:
    """May a pattern read this reply?

    The order matters. An exact option short-circuits everything below it,
    because "1" and "2" are positional -- they carry no vocabulary at all, so
    no word list and no chart can make them ambiguous. Everything after that
    is a reason to escalate.
    """
    text = normalize(answer)

    if not text:
        return ClarificationAmbiguity(False, "empty")

    if text in OPTION_FIRST or text in OPTION_SECOND:
        return ClarificationAmbiguity(True, "option")

    if _negated(text):
        return ClarificationAmbiguity(False, "negation")

    concepts = _concepts_present(text, missing_fields)
    if len(concepts) > 1:
        return ClarificationAmbiguity(False, "multiple_concepts")

    named = _named_accounts(text, accounts)
    codes = tuple(str(a.get("code")) for a in named)

    if len(concepts) == 1:
        concept = next(iter(concepts))
        expected = _CONCEPT_SUBTYPES.get(concept)
        if expected is not None and named:
            subtypes = {str(a.get("account_subtype") or "") for a in named}
            if not subtypes <= expected:
                # The reply names an account that is not what the concept
                # would resolve to -- "محفظة ون كاش" is an e_wallet and the
                # pattern would have said cash.
                return ClarificationAmbiguity(False, "chart_collision", codes)
        return ClarificationAmbiguity(True, "single_concept", codes)

    if named:
        # An account the patterns have no concept for at all -- every e-wallet
        # in the Yemen chart is one of these. The pattern would return None
        # and the user would be re-asked; it is escalated rather than passed
        # so that the interpretation step can resolve it once it exists.
        return ClarificationAmbiguity(False, "named_account_no_concept", codes)

    return ClarificationAmbiguity(False, "no_match")
