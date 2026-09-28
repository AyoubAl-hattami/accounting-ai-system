# -*- coding: utf-8 -*-
"""The detector and the resolver behind it must agree, and this is what says so.

THE INVARIANT
-------------
    For every reply the ambiguity detector calls UNAMBIGUOUS, the resolver
    that will then be asked to read it must return a value.

That is the whole file. Everything else here is corpus, plumbing, or a check
that this check still bites.

WHY IT EXISTS
-------------
``clarification_ambiguity`` decides whether a reply is safe for a pattern.
When it says yes, ``_apply_clarification_answer`` runs a resolver, and if that
resolver returns ``None`` the caller sets ``changed = False`` and the user is
told **"لم أفهم إجابتك"** and shown the same two options again. That sentence
is the failure this whole redesign was built to remove. It can reappear
without any code changing behaviour on purpose: the detector and the resolvers
only have to describe the same reply differently.

They did. The resolvers restated the detector's option sets instead of
importing them, the detector accepted three spelled-out ordinals the
transaction-type resolver did not, and because an exact option match
SHORT-CIRCUITS every other rule in the detector, those three arrived at a
resolver that answered ``None``. Nine field/reply pairs, none covered by any
test. That is RAG-20 in ``docs/open-findings.md``.

Sharing the word lists closed those nine. It does not close the class: a word
added to either side, a resolver given a new early return, a field routed to a
different resolver -- each reopens it, silently, and the suite would not
notice. It did not notice for as long as the divergence existed. So the fix
that matters is this assertion, not that import.

WHAT THIS FILE DELIBERATELY DOES NOT PROVE
------------------------------------------
Three things can go wrong in the agreement between the field name being
clarified and the code that reads a reply to it. This file asserts the first
and (partly) the second, and cannot see the third:

1. a name the detector certifies and the resolver cannot read
   -> ``test_every_reply_the_detector_certifies_can_be_read``
2. a name that is produced but that no consumer branches on, so every reply
   escalates and the instant path quietly dies
   -> ``test_every_producible_field_has_a_resolver_or_is_a_recorded_gap``,
      which currently records ``account_mapping`` as exactly that
3. a resolver that answers a question which was not asked -- it returns a
   value, so the invariant above passes, and the value is wrong

Row 3 is unasserted and is why RAG-21 stays open. Read that entry before
assuming this file covers the subject.

This one imports the service, so unlike ``test_assistant_handler_gate_coverage``
it is not a static-job test: the invariant is about what the resolvers actually
return, and that cannot be read off the AST.
"""

import ast
import itertools
import pathlib

from app.modules.accounting.services import gemini_assistant_service as svc
from app.modules.accounting.services.clarification_ambiguity import (
    BANK_TERMS,
    CASH_TERMS,
    CUSTOMER_TERMS,
    EXPENSE_TERMS,
    INCOME_TERMS,
    NEGATION_TOKENS,
    OPTION_FIRST,
    OPTION_SECOND,
    SUPPLIER_TERMS,
    clarification_ambiguity,
)

SERVICE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "app" / "modules" / "accounting" / "services" / "gemini_assistant_service.py"
)

# A chart shaped like the one RAG-19 was measured on, plus one account whose
# name CONTAINS a concept term ("بنك الكريمي") and one that does not collide at
# all. The detector reads the chart, so a corpus tested against an empty chart
# would exercise a different function than production runs.
CHART = [
    {"code": "1100", "name": "الصندوق", "account_subtype": "cash", "is_active": True},
    {"code": "1110", "name": "البنك", "account_subtype": "bank", "is_active": True},
    {"code": "1120", "name": "بنك الكريمي", "account_subtype": "bank", "is_active": True},
    {"code": "1130", "name": "محفظة ون كاش", "account_subtype": "e_wallet", "is_active": True},
    {"code": "1140", "name": "محفظة جيب", "account_subtype": "e_wallet", "is_active": True},
    {"code": "1200", "name": "العملاء", "account_subtype": "receivable", "is_active": True},
]

# Which resolver reads a reply to which question. This is the coupling the
# invariant is about, so it is written once, here, and
# `test_the_resolver_map_matches_what_the_service_dispatches_on` checks it
# against the service's own dispatch rather than trusting it.
RESOLVED_BY = {
    "payment_source": svc._resolve_bank_cash_answer,
    "receiving_account": svc._resolve_bank_cash_answer,
    "transaction_type": lambda reply: svc._resolve_transaction_type_answer(
        reply, "transaction_type"
    ),
}

# Field names that can be produced and that NOTHING resolves. Each needs a
# reason, and the reason has to be the measured consequence, not an intention.
#
# account_mapping: `_missing_fields_for` returns it as its fallback when the
# mapper needs clarification but no specific field is missing. No consumer
# branches on it: `_concepts_present` finds no candidate concepts, so every
# reply naming anything escalates, and the three option replies are certified
# and then resolve nothing. Measured -- all eight replies of a probe corpus
# resolved nothing, for every reply shape. It is the live instance of RAG-21's
# second row. It is recorded rather than fixed because the question it belongs
# to is not "bank or cash?" and has no options; giving it a resolver is a
# different piece of work.
NO_RESOLVER = {"account_mapping"}

# This briefly held "supplier_or_expense" and "customer_or_income" -- names
# every consumer branched on and nothing produced. They are gone from the
# service, the detector and the interpreter, so the equality below needs no
# exemption set at all. Keeping the name here, empty, would invite one back;
# if a name ever has to be exempted again, add the set with its reason in the
# same commit that adds the name. See RAG-21.


# ── the corpus ──────────────────────────────────────────────────────────────
# Closed where the thing being enumerated is closed. Both option sets and all
# six vocabulary lists are finite and are used in full; the chart is finite and
# is used in full. The combinations are bounded products of those, which is
# where a reply that carries two ideas comes from.

ALL_TERMS = tuple(
    itertools.chain(
        BANK_TERMS, CASH_TERMS, SUPPLIER_TERMS,
        EXPENSE_TERMS, CUSTOMER_TERMS, INCOME_TERMS,
    )
)
CHART_WORDS = tuple(a["name"] for a in CHART) + tuple(a["code"] for a in CHART)
OPTIONS = tuple(sorted(OPTION_FIRST | OPTION_SECOND))
# Arabic-Indic and extended digits, which `normalize` folds, plus case, which
# it lowers. A corpus of pre-normalised strings would not test either.
SHAPE_VARIANTS = ("١", "٢", "۱", "۲", "Bank", "CASH", "  bank  ", "Mورد")


def _corpus() -> tuple[str, ...]:
    replies: list[str] = []
    replies.extend(OPTIONS)
    replies.extend(ALL_TERMS)
    replies.extend(CHART_WORDS)
    replies.extend(SHAPE_VARIANTS)
    # two ideas in one reply, in both orders
    replies.extend(f"{a} {b}" for a, b in itertools.product(ALL_TERMS, ALL_TERMS) if a != b)
    # a polarity marker with each term -- the RAG-19 shape
    replies.extend(f"{n} {t}" for n, t in itertools.product(sorted(NEGATION_TOKENS), ALL_TERMS))
    # a concept term next to a real account name -- the chart-collision shape
    replies.extend(f"{t} {w}" for t, w in itertools.product(ALL_TERMS, CHART_WORDS))
    # an option next to something else, which must not stay a bare option
    replies.extend(f"{o} {t}" for o, t in itertools.product(OPTIONS, ALL_TERMS[:6]))
    return tuple(dict.fromkeys(replies))


CORPUS = _corpus()


def _violations(field, resolver, replies=CORPUS, chart=CHART):
    """Replies this field's detector certifies and its resolver cannot read.

    Shared by the real invariant and by the test that proves the invariant
    bites, so the two cannot drift apart either.
    """
    found = []
    for reply in replies:
        verdict = clarification_ambiguity(reply, chart, [field])
        if verdict.unambiguous and resolver(reply) is None:
            found.append((field, reply, verdict.reason))
    return found


def _certified(field, replies=CORPUS, chart=CHART):
    return [r for r in replies if clarification_ambiguity(r, chart, [field]).unambiguous]


# ── the invariant ───────────────────────────────────────────────────────────


def test_every_reply_the_detector_certifies_can_be_read():
    """The one assertion this file is for.

    A failure here is not "the corpus found a weird string". It is: the
    instant path will answer this reply with "لم أفهم إجابتك" while the
    detector believes it is unambiguous, and the escalation that would have
    read it correctly was skipped.
    """
    violations = [
        v for field, resolver in RESOLVED_BY.items()
        for v in _violations(field, resolver)
    ]
    assert violations == [], (
        f"{len(violations)} certified replies no resolver can read; "
        f"first few: {violations[:12]}"
    )


def test_the_replies_that_opened_rag_20_resolve():
    """Named explicitly, so a corpus change cannot quietly drop them.

    RAG-20 counted nine field/reply pairs: three replies across three field
    names. Six of the nine sat behind names nothing produced and went away with
    those names; these three are the reachable ones. The invariant above would
    catch them anyway -- they are spelled out because a regression here is the
    exact user-visible bug, and a named test says so in its failure message.
    """
    for reply in ("واحد", "اتنين", "اثنين"):
        verdict = clarification_ambiguity(reply, CHART, ["transaction_type"])
        assert verdict.unambiguous, f"{reply!r} is no longer certified"
        assert RESOLVED_BY["transaction_type"](reply) is not None, (
            f"{reply!r} is certified and resolves to None -- RAG-20 again"
        )


def test_the_invariant_bites_when_the_option_sets_are_pulled_apart():
    """Proof that the test above is not vacuous, kept rather than performed.

    The option sets were separate until RAG-20. This puts the transaction-type
    resolver back on its old literal sets and asserts the invariant then FAILS,
    naming the reply it failed on. Without this, a future refactor that made
    `_violations` silently return nothing would look like success.
    """
    def pre_rag_20_resolver(reply):
        """`_resolve_transaction_type_answer` as it stood at 9aee18d, for
        missing_field="transaction_type". Faithful, including the customer and
        income branches that are not gated on the field -- a stub that dropped
        them would fail this test for the wrong reason, which is how this
        version came to be written."""
        text = svc._normalize_clarification_answer(reply)
        if text in {"1", "اول", "الأول", "الاول"}:
            return "supplier_payment"
        if text in {"2", "ثاني", "الثاني"}:
            return "expense_payment"
        if any(term in text for term in SUPPLIER_TERMS):
            return "supplier_payment"
        if any(term in text for term in EXPENSE_TERMS):
            return "expense_payment"
        if any(term in text for term in CUSTOMER_TERMS):
            return "customer_receipt"
        if any(term in text for term in INCOME_TERMS):
            return "income_receipt"
        return None

    violations = _violations("transaction_type", pre_rag_20_resolver)
    replies = {reply for _, reply, _ in violations}
    assert violations, "the invariant passed against the resolver RAG-20 was filed about"
    assert {"واحد", "اتنين", "اثنين"} <= replies, (
        f"it failed, but not on the three replies RAG-20 names: {sorted(replies)[:12]}"
    )
    assert all(reason == "option" for _, _, reason in violations), (
        "the divergence should be reached through the option short-circuit; "
        f"reasons seen: {sorted({r for _, _, r in violations})}"
    )


def test_the_corpus_is_large_and_certifies_a_real_share_of_it():
    """A corpus that certified nothing would satisfy the invariant trivially."""
    assert len(CORPUS) > 500, f"corpus collapsed to {len(CORPUS)} replies"
    for field in RESOLVED_BY:
        certified = _certified(field)
        assert len(certified) >= 10, (
            f"only {len(certified)} replies are certified for {field}; the "
            "invariant is close to vacuous for it"
        )


# ── the coupling the invariant depends on ───────────────────────────────────


def _function(name: str) -> ast.FunctionDef:
    tree = ast.parse(SERVICE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in {SERVICE.name}")


def _fields_dispatched_on() -> set[str]:
    """Field names `_apply_clarification_answer` actually branches on.

    Read from the source, so adding a field to the service without adding it
    to RESOLVED_BY fails here instead of leaving an unasserted resolver. Two
    shapes: a literal tested directly against `missing`, and the tuple of
    names the function loops over while testing each against `missing`.
    """
    function = _function("_apply_clarification_answer")
    found: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Compare) and any(isinstance(op, ast.In) for op in node.ops):
            names = {
                c.id for c in node.comparators if isinstance(c, ast.Name)
            }
            if "missing" in names and isinstance(node.left, ast.Constant):
                found.add(node.left.value)
    for node in ast.walk(function):
        if not isinstance(node, ast.For) or not isinstance(node.iter, ast.Tuple):
            continue
        tests_missing = any(
            isinstance(inner, ast.Compare)
            and any(isinstance(op, ast.In) for op in inner.ops)
            and any(
                isinstance(c, ast.Name) and c.id == "missing" for c in inner.comparators
            )
            for statement in node.body
            for inner in ast.walk(statement)
        )
        if tests_missing:
            found.update(
                element.value for element in node.iter.elts
                if isinstance(element, ast.Constant)
            )
    return found


def test_the_resolver_map_matches_what_the_service_dispatches_on():
    """RESOLVED_BY is the test's claim about production; this checks it."""
    assert _fields_dispatched_on() == set(RESOLVED_BY), (
        "the service dispatches on a different set of fields than this file "
        f"declares: service={sorted(_fields_dispatched_on())} "
        f"declared={sorted(RESOLVED_BY)}"
    )


def _producible_fields() -> set[str]:
    """Every field name `_missing_fields_for` can put in a pending envelope.

    Only names it APPENDS to the list or RETURNS. The function also names
    transaction types in two membership sets, and counting those made this read
    the wrong thing entirely -- the first version of this helper reported seven
    transaction types as producible field names.
    """
    function = _function("_missing_fields_for")
    found: set[str] = set()
    for node in ast.walk(function):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "append"
        ):
            found.update(
                argument.value for argument in node.args
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
            )
        if isinstance(node, ast.Return) and node.value is not None:
            found.update(
                inner.value for inner in ast.walk(node.value)
                if isinstance(inner, ast.Constant) and isinstance(inner.value, str)
            )
    return found


def test_every_producible_field_has_a_resolver_or_is_a_recorded_gap():
    """RAG-21's second row, as far as it can be asserted here.

    A field name that is produced and that nothing branches on does not fail
    anything: the detector answers "escalate", which is a legal answer, and
    the user is re-asked or the reply is paid for. This is the only place that
    would say so.
    """
    producible = _producible_fields()
    accounted_for = set(RESOLVED_BY) | NO_RESOLVER
    assert producible == accounted_for, (
        "a produced field name is neither resolved nor recorded as a gap: "
        f"{sorted(producible - accounted_for)}; "
        "or a name is resolved here and produced nowhere, which makes its "
        "branches unreachable and should be deleted: "
        f"{sorted(accounted_for - producible)}"
    )


def test_the_recorded_gap_still_behaves_the_way_it_was_recorded():
    """Characterisation, not approval.

    `account_mapping` resolves nothing, for every reply shape. If that ever
    stops being true, this fails -- and the right response is to update RAG-21
    and move the field into RESOLVED_BY, not to delete this test.
    """
    pending = svc.PendingTransaction(
        company_id=1, transaction_type="expense_payment", amount=300.0,
        description="", missing_fields=["account_mapping"],
    )
    parsed = svc._parsed_from_pending(pending)
    resolved_something = [
        reply for reply in CORPUS[:200]
        if svc._apply_clarification_answer(parsed, pending, reply)[1]
    ]
    assert resolved_something == [], (
        "account_mapping now resolves something; RAG-21 needs updating: "
        f"{resolved_something[:8]}"
    )
