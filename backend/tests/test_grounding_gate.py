"""The gate, proved where the figures are already trustworthy.

The deterministic handlers format one set of Decimals into both the sentence
and the card, so their replies are the one corpus where prose and grounding
are known to agree. If the gate refuses those, the gate is wrong -- and it
would have been wrong in the direction that matters, because a gate that
cries wolf gets switched off.

The rest of the file is the other direction: what it must refuse, and the
three things it cannot see, asserted rather than claimed.
"""

from decimal import Decimal

import pytest

from app.modules.accounting.schemas.gemini_assistant_schemas import (
    JournalEvidenceEntry,
    JournalEvidenceGrounding,
    JournalEvidenceSummary,
    PageContext,
    ProfitAndLossGrounding,
    ProfitAndLossMetrics,
    ProfitAndLossPeriod,
    ProfitAndLossReference,
    TrialBalanceGrounding,
)
from app.modules.accounting.services import gemini_assistant_service as service
from app.modules.accounting.services import grounding_gate


def _profit_and_loss(revenue="4000.00", expenses="1500.00", net="2500.00"):
    return ProfitAndLossGrounding(
        status="grounded",
        kind="profit_and_loss",
        requested_metric="net_profit",
        period=ProfitAndLossPeriod(start_date="2026-01-01", end_date="2026-01-31", label="January"),
        metrics=ProfitAndLossMetrics(revenue=revenue, expenses=expenses, net_profit=net),
        reference=ProfitAndLossReference(
            type="report", report="profit_and_loss",
            filters={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        ),
    )


def _trial_balance(debit="4000.00", credit="4000.00"):
    return TrialBalanceGrounding(
        status="grounded",
        kind="trial_balance",
        metrics={"total_debit": debit, "total_credit": credit, "difference": "0.00", "is_balanced": True},
    )


# ── Proved against the deterministic path ────────────────────────────────────

DETERMINISTIC_QUESTIONS = [
    "What is our profit this month?",
    "What are total expenses?",
    "How much revenue did we make?",
    "Show me the trial balance",
    "What is the balance sheet?",
    "Who entered 1500?",
]


@pytest.mark.parametrize("question", DETERMINISTIC_QUESTIONS)
def test_the_gate_vouches_for_the_deterministic_path(question, accounting_factory):
    """Every figure a deterministic handler prints is a figure it grounded."""
    bootstrap = accounting_factory.create_accounting_bootstrap(role="admin")
    accounting_factory.create_balanced_journal(bootstrap=bootstrap, amount=Decimal("1500.00"))

    reply = service.dispatch_gemini_assistant(
        db=accounting_factory.db,
        company_id=bootstrap.company.id,
        user_role="admin",
        message=question,
        page_context=PageContext(page="dashboard", route="/dashboard"),
        language="en",
    )
    if reply.grounding is None or getattr(reply.grounding, "status", None) != "grounded":
        pytest.skip(f"{question!r} produced no grounded card to check")

    unvouched = grounding_gate.unvouched_numbers(reply.reply, reply.grounding)
    assert not unvouched, (
        f"The gate refused a deterministic reply, which formats the same "
        f"Decimals into both halves. Numbers it could not account for: "
        f"{unvouched}. Reply was: {reply.reply[:200]}"
    )


def test_at_least_one_deterministic_question_really_was_grounded(accounting_factory):
    """Guard the guard: if every case above skipped, the proof proved nothing."""
    bootstrap = accounting_factory.create_accounting_bootstrap(role="admin")
    accounting_factory.create_balanced_journal(bootstrap=bootstrap, amount=Decimal("1500.00"))

    grounded = 0
    for question in DETERMINISTIC_QUESTIONS:
        reply = service.dispatch_gemini_assistant(
            db=accounting_factory.db,
            company_id=bootstrap.company.id,
            user_role="admin",
            message=question,
            page_context=PageContext(page="dashboard", route="/dashboard"),
            language="en",
        )
        if reply.grounding is not None and getattr(reply.grounding, "status", None) == "grounded":
            grounded += 1
    assert grounded, "No deterministic question produced a grounded card."


# ── What it vouches for ──────────────────────────────────────────────────────

def test_a_reply_quoting_the_report_is_vouched():
    text = "Revenue was 4000.00 and expenses 1500.00, so net profit is 2500.00 for January."
    decision = grounding_gate.decide(text, [_profit_and_loss()])
    assert decision.attach and decision.verified
    assert decision.reason == "vouched"


def test_the_same_figure_written_differently_is_the_same_figure():
    decision = grounding_gate.decide("Net profit is 2,500.00.", [_profit_and_loss()])
    assert decision.attach, "1,500.00 and 1500.00 are one number written two ways."


def test_account_codes_and_dates_do_not_count_against_a_reply():
    text = "Between 2026-01-01 and 2026-01-31, net profit was 2500.00."
    assert grounding_gate.decide(text, [_profit_and_loss()]).attach


# ── What it refuses ──────────────────────────────────────────────────────────

def test_an_invented_figure_takes_the_card_off():
    decision = grounding_gate.decide("Net profit is 9999.99.", [_profit_and_loss()])
    assert not decision.attach
    assert decision.reason == "unvouched_numbers"
    assert decision.unvouched == ("9999.99",)
    assert decision.grounding is None, "Refusal means no card, not a card with a caveat."


def test_two_kinds_in_one_turn_attach_nothing():
    """The failure mode last-grounded-wins would produce, refused instead."""
    text = "Revenue was 4000.00."
    decision = grounding_gate.decide(text, [_profit_and_loss(), _trial_balance()])
    assert not decision.attach
    assert decision.reason == "several_kinds"
    assert decision.unvouched == ("profit_and_loss", "trial_balance")


def test_the_same_kind_twice_takes_the_last():
    january = _profit_and_loss(net="2500.00")
    february = _profit_and_loss(revenue="10.00", expenses="10.00", net="7777.00")
    decision = grounding_gate.decide("Net profit is 7777.00.", [january, february])
    assert decision.attach and decision.grounding is february


def test_an_unavailable_report_is_not_a_card():
    unavailable = ProfitAndLossGrounding(status="unavailable", kind="profit_and_loss")
    decision = grounding_gate.decide("Net profit is 2500.00.", [unavailable])
    assert not decision.attach
    assert decision.reason == "grounding_unavailable"


def test_no_grounding_means_no_card():
    decision = grounding_gate.decide("Net profit is 2500.00.", [])
    assert not decision.attach and decision.reason == "no_grounding"
    assert decision.verified is False


def test_evidence_entries_vouch_for_the_amounts_they_carry():
    grounding = JournalEvidenceGrounding(
        status="grounded",
        kind="journal_evidence",
        basis="amount_trace",
        summary=JournalEvidenceSummary(total_matches=1, returned_matches=1, has_more=False),
        entries=[
            JournalEvidenceEntry(
                journal_entry_id=42, entry_number="JE-0042", entry_date="2026-01-05",
                description="rent", status="posted", source="manual", creator_name="A",
                total_debit="1500.00", total_credit="1500.00", matched_amount="1500.00",
                match_reason="debit_line",
            )
        ],
    )
    decision = grounding_gate.decide(
        "Entry JE-0042 on 2026-01-05 carries 1500.00.", [grounding]
    )
    assert decision.attach


# ── The three gaps, asserted rather than claimed ─────────────────────────────

def test_gap_a_right_number_under_the_wrong_label_passes():
    """1500.00 is the EXPENSE total. The gate reads numbers, not sentences."""
    decision = grounding_gate.decide("Revenue was 1500.00.", [_profit_and_loss()])
    assert decision.attach, (
        "Documenting the gap: closing it needs the label checked against the "
        "field the figure came from, which the grounding does not record."
    )


def test_gap_b_a_figure_with_no_digits_passes():
    decision = grounding_gate.decide(
        "Net profit was roughly two and a half thousand.", [_profit_and_loss()]
    )
    assert decision.attach, "There is no token to compare."


def test_gap_c_a_derived_figure_that_lands_on_a_known_number_passes():
    """Revenue minus expenses stated as 'total costs' is arithmetic the model
    did; it is indistinguishable from a quote because the value is present."""
    decision = grounding_gate.decide("Total costs came to 2500.00.", [_profit_and_loss()])
    assert decision.attach


def test_the_gaps_are_documented_where_the_gate_is():
    """A reader deciding whether to trust the badge must find the limits in
    the module, not in a commit message."""
    import inspect

    source = inspect.getsource(grounding_gate)
    assert "WHAT THIS DOES NOT CATCH" in source
    for gap in ("wrong label", "no digits", "coincidence"):
        assert gap in source, f"The module does not name the {gap!r} gap."
