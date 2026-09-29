"""The model answers only what no deterministic handler claimed.

The tool-calling stage is the registered handler for ``unknown``. Two rules
decide whether that is safe, and both are asserted here rather than argued:

  1. A question a deterministic handler claims never reaches the model. In an
     accounting system the figure comes from the report service; the model may
     narrate one, never produce one.
  2. When the model declines -- no key, no budget, provider down, empty answer
     -- the caller says exactly what it said before the stage existed.

No network: the model is a stub that fails or is never constructed, and the
session is a MagicMock.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.modules.accounting.schemas.gemini_assistant_schemas import (
    GeminiAssistantReply,
    PageContext,
)
from app.modules.accounting.services import gemini_assistant_service as service
from app.modules.accounting.services import unified_gemini_agent
from app.modules.accounting.services.assistant_handler_registry import (
    ASSISTANT_HANDLERS,
    _CAN_READ_REPORTS,
)

PAGE = PageContext(page="dashboard", route="/dashboard")

# Claimed by a deterministic handler, and what claims it.
DETERMINISTIC = [
    ("What is our profit this month?", "answer_report_question"),
    ("Show me the last journal entry", "answer_journal_question"),
    # Measured, not assumed: this one classifies as an AUDIT question, not a
    # user question. That is a misclassification and it is pre-existing --
    # what matters here is that a deterministic handler claims it, so the
    # model never sees it.
    ("Who are the active users?", "answer_audit_question"),
]

# Claimed by nobody: every one of these is about the subledger, which has 12
# tools and no handler at all.
UNCLASSIFIED = [
    "What does customer Bravo Secret Supplier owe us?",
    "Which credit notes are still unallocated?",
    "tell me about invoice INV-2001",
    "Summarise our cash position and outstanding bills",
    "How are our receivables ageing?",
    "list the partners we buy from",
    "what is the status of our supplier bills",
    "give me the aging buckets for customers",
]


def _dispatch(message, role="admin", db=None):
    return service.dispatch_gemini_assistant(
        db=db if db is not None else MagicMock(),
        company_id=1,
        user_role=role,
        message=message,
        page_context=PAGE,
        language="en",
    )


def _stage_spy(calls):
    def _spy(**kwargs):
        calls.append(kwargs["message"])
        return None

    return _spy


@pytest.mark.parametrize("message,expected_intent", DETERMINISTIC)
def test_a_deterministic_handler_keeps_its_question(monkeypatch, message, expected_intent):
    monkeypatch.setattr(service.settings, "GEMINI_API_KEY", "probe-key")
    calls: list[str] = []
    monkeypatch.setattr(unified_gemini_agent, "answer_with_tools", _stage_spy(calls))
    # The deterministic handlers phrase some answers through the model; that is
    # narration of a figure the report service produced, and it is not what
    # this test is about.
    monkeypatch.setattr(service, "_call_gemini_for_answer", lambda *a, **k: None)

    reply = _dispatch(message)

    assert calls == [], (
        f"{message!r} reached the model stage, but {expected_intent} claims it. "
        "A figure must come from the report service."
    )
    assert reply.intent == expected_intent


@pytest.mark.parametrize("message", UNCLASSIFIED)
def test_a_question_nobody_claims_reaches_the_model(monkeypatch, message):
    monkeypatch.setattr(service.settings, "GEMINI_API_KEY", "probe-key")
    calls: list[str] = []
    monkeypatch.setattr(unified_gemini_agent, "answer_with_tools", _stage_spy(calls))

    _dispatch(message)

    assert calls == [message], (
        f"{message!r} never reached the model stage. Before this stage existed "
        "it was answered with 'Which accounting question would you like help "
        "with?', which is the answer the subledger questions all got."
    )


def test_the_model_answer_is_returned_when_it_answers(monkeypatch):
    monkeypatch.setattr(service.settings, "GEMINI_API_KEY", "probe-key")
    answered = GeminiAssistantReply(
        reply="Bravo Secret Supplier owes 31,337.00 on INV-BRAVO-9001.",
        intent="unified_agent_response",
        confidence="high",
        data_sources=["database"],
    )
    monkeypatch.setattr(unified_gemini_agent, "answer_with_tools", lambda **kwargs: answered)

    reply = _dispatch("What does customer Bravo Secret Supplier owe us?")

    assert reply.reply == answered.reply
    assert reply.intent == "unified_agent_response"


def test_a_declined_stage_leaves_the_answer_exactly_as_it_was(monkeypatch):
    """The reply with a model that declines must equal the reply with no model."""
    message = "Which credit notes are still unallocated?"

    monkeypatch.setattr(service.settings, "GEMINI_API_KEY", "probe-key")
    monkeypatch.setattr(unified_gemini_agent, "answer_with_tools", lambda **kwargs: None)
    declined = _dispatch(message)

    monkeypatch.setattr(service.settings, "GEMINI_API_KEY", "")
    without_model = _dispatch(message)

    assert declined.reply == without_model.reply
    assert declined.intent == without_model.intent
    assert declined.intent == "clarification"


def test_the_stage_is_registered_and_gated():
    """It is a registry entry like the other nine, which is what puts it
    inside the invariants in test_assistant_handler_gate_coverage."""
    entries = [entry for entry in ASSISTANT_HANDLERS if "unknown" in entry.intents]
    assert len(entries) == 1, "unknown is dispatched by exactly one entry."
    entry = entries[0]
    assert entry.permission is _CAN_READ_REPORTS
    assert entry.denial.reply_for("ar") and entry.denial.reply_for("en")
    # Last: every deterministic entry is consulted before it.
    assert ASSISTANT_HANDLERS[-1] is entry


def test_a_role_outside_the_gate_is_refused_before_the_model_is_called(monkeypatch):
    monkeypatch.setattr(service.settings, "GEMINI_API_KEY", "probe-key")
    calls: list[str] = []
    monkeypatch.setattr(unified_gemini_agent, "answer_with_tools", _stage_spy(calls))

    with patch.object(
        service, "_unknown_handler_entry",
        lambda: type(ASSISTANT_HANDLERS[-1])(
            intents=("unknown",),
            permission=frozenset({"admin"}),
            denial=ASSISTANT_HANDLERS[-1].denial,
            handler=ASSISTANT_HANDLERS[-1].handler,
        ),
    ):
        reply = _dispatch("tell me about invoice INV-2001", role="viewer")

    assert reply.intent == "access_denied"
    assert calls == [], "The gate ran after the model rather than before it."
