"""trace_amount answers from the deterministic path's query, and carries its card.

The tool had its own query: a join with DISTINCT ordered by date, returning
entry number, date, description, status and the matched amount. That is
strictly less than JournalEvidenceGrounding records -- no actor, no source,
no match reason, no count of matches beyond the page -- so it could not have
produced a card even if something had asked it to.

It now delegates to _tool_trace_amount, which the trace handler has used all
along, and builds the card with _build_journal_evidence, which the trace
handler has used all along. One query, one card builder, two callers.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.modules.accounting.services import accounting_tool_registry as registry
from app.modules.accounting.services import grounding_gate

MATCH = {
    "id": 42,
    "entry_no": "JE-0042",
    "entry_date": "2026-01-05",
    "description": "rent for January",
    "status": "posted",
    "source_type": "manual",
    "amount": Decimal("1500.00"),
    "total_debit": "1500.00",
    "total_credit": "1500.00",
    "match_reason": "debit_line",
    "debit_accounts": ["Rent Expense"],
    "credit_accounts": ["Main Bank"],
    "created_by": "Alpha Admin",
    "posted_by": "Alpha Admin",
    "total_matches": 3,
}

DRAFT_MATCH = {**MATCH, "id": 43, "entry_no": "JE-0043", "status": "draft", "total_matches": 3}


def _trace(matches, amount=1500.0):
    with patch.object(registry, "_tool_trace_amount", return_value=matches) as query:
        result = registry.tool_trace_amount(db=MagicMock(), company_id=1, amount=amount)
    return result, query


# ── One query ────────────────────────────────────────────────────────────────

def test_the_tool_delegates_rather_than_querying_again():
    result, query = _trace([MATCH])

    query.assert_called_once()
    assert query.call_args.kwargs["company_id"] == 1
    assert query.call_args.kwargs["amount"] == Decimal("1500.0")
    assert result.data["entries"]


def test_the_module_no_longer_carries_a_second_trace_query():
    """The old query is gone, not merely unused."""
    import inspect

    source = inspect.getsource(registry.tool_trace_amount)
    assert "select(" not in source, (
        "tool_trace_amount is building a query again; the point of this "
        "commit was that there is one."
    )


# ── The card ─────────────────────────────────────────────────────────────────

def test_the_card_is_the_evidence_the_query_returned():
    result, _ = _trace([MATCH])

    card = result.grounding
    assert card is not None
    assert card.kind == "journal_evidence"
    assert card.basis == "amount_trace"
    assert card.query == {"amount": "1500.00"}
    assert card.summary.total_matches == 3
    assert card.summary.returned_matches == 1
    assert card.summary.has_more is True, "Three matches, one page: the card says so."

    entry = card.entries[0]
    assert entry.entry_number == "JE-0042"
    assert entry.status == "posted"
    assert entry.matched_amount == "1500.00"
    assert entry.match_reason == "debit_line"
    assert entry.creator_name == "Alpha Admin"


def test_no_matches_means_no_card():
    result, _ = _trace([])

    assert result.data["entries"] == []
    assert result.grounding is None, (
        "An empty trace has nothing to verify; a card would be a badge over "
        "the absence of evidence."
    )


def test_a_failed_trace_says_so_and_carries_no_card():
    """_tool_trace_amount returns None when its query raises."""
    result, _ = _trace(None)

    assert "could not be completed" in result.data["error"]
    assert result.error == "trace_failed"
    assert result.grounding is None


# ── RAG-7 still holds ────────────────────────────────────────────────────────

def test_a_draft_is_traced_and_labelled():
    result, _ = _trace([MATCH, DRAFT_MATCH])

    labelled = {e["entry_no"]: e["counts_in_reports"] for e in result.data["entries"]}
    assert labelled == {"JE-0042": True, "JE-0043": False}
    assert result.data["reportable_statuses"] == ["posted", "reversed"]
    # And the card carries the status too, so a rendered card cannot show a
    # draft as though it were posted.
    assert {entry.status for entry in result.grounding.entries} == {"posted", "draft"}


# ── The gate, on what this tool produces ─────────────────────────────────────

def test_the_gate_vouches_for_a_reply_quoting_the_evidence():
    result, _ = _trace([MATCH])

    decision = grounding_gate.decide(
        "1500.00 appears in JE-0042 on 2026-01-05, debited to Rent Expense.",
        [result.grounding],
    )
    assert decision.attach and decision.verified


def test_the_gate_refuses_a_reply_that_invents_an_entry_amount():
    result, _ = _trace([MATCH])

    decision = grounding_gate.decide(
        "1500.00 appears in JE-0042, part of a 4,800.00 batch.", [result.grounding]
    )
    assert not decision.attach
    assert decision.unvouched == ("4,800.00",)
