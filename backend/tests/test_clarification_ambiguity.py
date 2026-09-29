# -*- coding: utf-8 -*-
"""The detector that decides whether a clarification reply may be pattern-matched.

Everything rests on this. RAG-19 is not fixed by this commit -- it is made
unreachable, which is a different and weaker property: the buggy resolvers
are still there, still wrong, and only ever see replies this detector has
cleared. If the detector lets one through, the silent-wrong-entry comes back
with no other test failing.

So the assertions below are in two groups, and they fail for opposite
reasons:

  * "stays instant" -- a regression here costs latency and quota once the
    interpretation step exists. Annoying, not dangerous.
  * "escalates" -- a regression here is a journal entry against an account
    the user ruled out. This is the group that matters.

Pure functions over dictionaries. No database, no HTTP, no service import,
no settings -- the module under test imports nothing but dataclasses and
typing, so this runs in the static CI job.
"""
import pytest

from app.modules.accounting.services.clarification_ambiguity import (
    ClarificationAmbiguity,
    NEGATION_SUBSTRINGS,
    NEGATION_TOKENS,
    clarification_ambiguity,
    normalize,
)

# The Yemen starter chart, which is the one that makes this hard: it has a
# cash account AND three e-wallets, one of which is named after the cash
# keyword. Written out rather than loaded so the test states the shape it
# depends on.
YEMEN = [
    {"code": "1100", "name": "الصندوق", "account_subtype": "cash", "is_active": True},
    {"code": "1110", "name": "بنك الكريمي", "account_subtype": "bank", "is_active": True},
    {"code": "1120", "name": "محفظة جوالي", "account_subtype": "e_wallet", "is_active": True},
    {"code": "1130", "name": "محفظة ون كاش", "account_subtype": "e_wallet", "is_active": True},
    {"code": "1140", "name": "محفظة جيب", "account_subtype": "e_wallet", "is_active": True},
    {"code": "1200", "name": "الذمم المدينة", "account_subtype": "receivable", "is_active": True},
]

# The English default chart, which has no cash account at all.
ENGLISH = [
    {"code": "1000", "name": "Assets", "account_subtype": None, "is_active": True},
    {"code": "1110", "name": "Main Bank", "account_subtype": "bank", "is_active": True},
    {"code": "1200", "name": "Accounts Receivable", "account_subtype": "receivable", "is_active": True},
]

SOURCE = ["payment_source"]
TYPE = ["transaction_type"]


# ── group 1: what must stay instant and free ────────────────────────────────


@pytest.mark.parametrize("reply", [
    "1", "2", "١", "٢", "۱", "۲",            # both Arabic-Indic digit ranges
    "اول", "الأول", "الاول", "واحد",
    "ثاني", "الثاني", "اتنين", "اثنين",
    " 1 ", "  الثاني  ",                       # whitespace
])
def test_offered_ordinals_never_escalate(reply):
    """Ordinals carry no vocabulary, so nothing can make them ambiguous.

    This is why the option test short-circuits before the negation test: "لا"
    is a substring of nothing here, but if the order were reversed a future
    ordinal containing a marker would start paying a round trip for no reason.
    """
    result = clarification_ambiguity(reply, YEMEN, SOURCE)
    assert result.unambiguous, f"{reply!r} escalated as {result.reason}"
    assert result.reason == "option"


@pytest.mark.parametrize("reply", [
    "البنك", "بنك", "مصرف", "bank", "من البنك",
    "الصندوق", "صندوق", "نقد", "نقدية", "cash",
])
def test_single_concept_answers_stay_instant(reply):
    """The plain answers to the question asked. These are the common case and
    they must not pay for the hard ones."""
    result = clarification_ambiguity(reply, YEMEN, SOURCE)
    assert result.unambiguous, f"{reply!r} escalated as {result.reason}"


def test_the_cash_account_agreeing_with_the_cash_concept_stays_instant():
    """الصندوق names account 1100 AND is the cash concept -- they agree.

    The collision rule must not fire merely because a reply names an account.
    If it did, the single most common Arabic answer would escalate, and the
    detector would be useless in the chart it was built for.
    """
    result = clarification_ambiguity("الصندوق", YEMEN, SOURCE)
    assert result.unambiguous
    assert result.reason == "single_concept"
    assert result.matched_accounts == ("1100",)


# ── group 2: what must escalate. a miss here is a wrong journal entry ───────


RAG_19_NEGATIONS = [
    "لا، خليها من الصندوق بدل البنك",
    "من الصندوق مش من البنك",
    "ليس من البنك، من الصندوق",
    "مش البنك",
    "لا بنك",
    "from cash not bank",
    "not bank, cash",
    "actually cash",
]


@pytest.mark.parametrize("reply", RAG_19_NEGATIONS)
def test_every_rag_19_negation_escalates(reply):
    """Each of these resolves to 'bank' today, silently, whatever was meant.

    If this test fails, RAG-19 is live again.
    """
    result = clarification_ambiguity(reply, YEMEN, SOURCE)
    assert not result.unambiguous, (
        f"{reply!r} was cleared for pattern matching. The resolver reads it as "
        "'bank' regardless of what it says, so this is a draft against the "
        "account the user just ruled out."
    )
    assert result.reason in {"negation", "multiple_concepts"}


@pytest.mark.parametrize("reply", ["ون كاش", "محفظة ون كاش"])
def test_the_wallet_named_after_the_cash_keyword_escalates(reply):
    """RAG-19's second case: كاش is in the cash term list and in this account's
    name, so the pattern picks the cash account and the wallet loses."""
    result = clarification_ambiguity(reply, YEMEN, SOURCE)
    assert not result.unambiguous, f"{reply!r} would resolve to 1100, not 1130"
    assert result.reason == "chart_collision"
    assert "1130" in result.matched_accounts


@pytest.mark.parametrize("reply", ["جيب", "من محفظة جيب", "محفظة جوالي", "1140"])
def test_accounts_the_patterns_have_no_concept_for_escalate(reply):
    """The user's original complaint. These produce the clarification loop
    today because no term list contains them; they escalate so the
    interpretation step can resolve them from the chart."""
    result = clarification_ambiguity(reply, YEMEN, SOURCE)
    assert not result.unambiguous
    assert result.reason == "named_account_no_concept"


@pytest.mark.parametrize("reply", [
    "الغ العملية", "خلاص الغيها", "لا، المبلغ 500 مش 300", "كانت امبارح",
    "cancel that", "never mind",
])
def test_abandon_and_replace_escalate(reply):
    """Unrepresentable by any resolver, so they must not be handed to one."""
    assert not clarification_ambiguity(reply, YEMEN, SOURCE).unambiguous


def test_empty_and_whitespace_escalate():
    for reply in ("", "   ", "\n"):
        result = clarification_ambiguity(reply, YEMEN, SOURCE)
        assert not result.unambiguous
        assert result.reason == "empty"


# ── the chart is READ, not assumed ──────────────────────────────────────────


def test_the_same_reply_routes_differently_on_different_charts():
    """This is the property that separates a chart-aware detector from a word
    list, and it is the whole reason the caller passes accounts in.

    "ون كاش" collides only because THIS company has an e-wallet named after
    the cash keyword. On a chart without one there is nothing to collide with.
    """
    on_yemen = clarification_ambiguity("ون كاش", YEMEN, SOURCE)
    on_english = clarification_ambiguity("ون كاش", ENGLISH, SOURCE)

    assert on_yemen.reason == "chart_collision"
    assert on_english.unambiguous, (
        "With no e-wallet in the chart there is no collision, so the cash "
        "keyword is unambiguous and must stay instant."
    )


def test_an_account_added_to_the_chart_changes_the_verdict():
    """A list cannot do this. Adding an account makes a previously safe reply
    unsafe, with no code change and no new vocabulary."""
    before = clarification_ambiguity("نقدية", ENGLISH, SOURCE)
    assert before.unambiguous

    with_wallet = ENGLISH + [
        {"code": "1150", "name": "محفظة نقدية", "account_subtype": "e_wallet",
         "is_active": True},
    ]
    after = clarification_ambiguity("نقدية", with_wallet, SOURCE)
    assert not after.unambiguous
    assert after.reason == "chart_collision"
    assert "1150" in after.matched_accounts


def test_inactive_accounts_are_not_matched():
    """An archived account cannot create a collision -- map_to_accounts would
    not resolve to it either."""
    archived = [dict(a) for a in YEMEN]
    for account in archived:
        if account["code"] == "1130":
            account["is_active"] = False
    assert clarification_ambiguity("ون كاش", archived, SOURCE).unambiguous


def test_an_empty_chart_still_decides():
    """A company with no accounts, or a failed account read, must not crash
    the detector -- _tool_get_accounts returns [] on any exception."""
    assert clarification_ambiguity("البنك", [], SOURCE).unambiguous
    assert not clarification_ambiguity("مش البنك", [], SOURCE).unambiguous


# ── the question asked decides which concepts count ─────────────────────────


def test_concepts_are_counted_against_the_question_that_was_asked():
    """"bank or cash" and "supplier or expense" are different questions.

    A reply naming one concept from each is not ambiguous about either, so
    the count is scoped to the missing field rather than taken globally.
    """
    reply = "من البنك، مورد"
    assert clarification_ambiguity(reply, YEMEN, SOURCE).unambiguous is True
    assert clarification_ambiguity(reply, YEMEN, TYPE).unambiguous is True


def test_two_concepts_from_the_same_question_escalate():
    assert not clarification_ambiguity("البنك أو الصندوق", YEMEN, SOURCE).unambiguous
    assert not clarification_ambiguity("مورد أو مصروف", YEMEN, TYPE).unambiguous


# ── guard the guard ─────────────────────────────────────────────────────────


def test_the_detector_never_resolves_anything():
    """It answers one question and returns no field value.

    If it ever starts returning a resolved answer it has become a second
    matching stage, which is the thing this design exists to avoid.
    """
    result = clarification_ambiguity("البنك", YEMEN, SOURCE)
    assert isinstance(result, ClarificationAmbiguity)
    assert set(result.__dataclass_fields__) == {
        "unambiguous", "reason", "matched_accounts",
    }


def test_negation_markers_are_over_inclusive_on_purpose():
    """Every marker must escalate on its own, even inside a plausible answer.

    The list is allowed to be crude. A false escalation costs a round trip; a
    missed one costs a ledger entry. This asserts the crude direction.
    """
    for marker in NEGATION_TOKENS:
        reply = f"البنك {marker}"
        assert not clarification_ambiguity(reply, YEMEN, SOURCE).unambiguous, (
            f"token marker {marker!r} did not escalate"
        )
    for fragment in NEGATION_SUBSTRINGS:
        reply = f"that is{fragment} the bank"
        assert not clarification_ambiguity(reply, YEMEN, SOURCE).unambiguous, (
            f"substring marker {fragment!r} did not escalate"
        )


def test_normalize_is_the_one_used_by_the_resolvers():
    """The detector and the resolvers must agree on what the text IS before
    they can agree on what it means."""
    from app.modules.accounting.services import gemini_assistant_service as service

    for raw in ("  ١  ", "BANK", "الصندوق", " مش البنك "):
        assert normalize(raw) == service._normalize_clarification_answer(raw)
