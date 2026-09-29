"""The tool stage answers with the accounting tools, or declines.

It used to be an entry point that fell back to the deterministic assistant on
every failure, and these tests asserted that fallback -- which meant they
passed while asserting nothing about the agent: with no key configured, every
one of them was measuring dispatch_gemini_assistant.

It is now the handler for `unknown`, dispatched from inside that same
assistant, so it cannot delegate back without recursing. It returns None
instead, and the caller falls back to the capability menu. That contract is
what is asserted here.

No network: the Gemini client is a stub, and the session is a MagicMock.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.modules.accounting.schemas.gemini_assistant_schemas import PageContext
from app.modules.accounting.services import unified_gemini_agent
from app.modules.accounting.services.ai_providers.gemini_provider import (
    model_calls_suppressed,
    request_budget,
)
from app.modules.accounting.services.unified_gemini_agent import answer_with_tools


@pytest.fixture
def mock_db():
    return MagicMock()


# ── A stub shaped like the SDK response the loop reads ───────────────────────

class _Part:
    def __init__(self, text=None):
        self.text = text


class _Content:
    def __init__(self, parts):
        self.parts = parts
        self.role = "model"


class _Candidate:
    def __init__(self, parts):
        self.content = _Content(parts)


class _Response:
    def __init__(self, text=None, function_calls=None):
        self.text = text
        self.function_calls = function_calls or []
        self.candidates = [_Candidate([_Part(text)] if text else [])]


class _FunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class _StubClient:
    """Returns the queued responses in order; records the configs it was given."""

    def __init__(self, responses, **kwargs):
        self._responses = list(responses)
        self.configs = []
        self.models = self
        self.kwargs = kwargs

    def generate_content(self, *, model, contents, config):
        self.configs.append(config)
        return self._responses.pop(0)


def _answer(message="What is our profit and loss?", role="admin", db=None):
    return answer_with_tools(
        db=db if db is not None else MagicMock(),
        company_id=1,
        user_role=role,
        message=message,
        page_context=PageContext(page="reports", route="/reports/profit-and-loss"),
        language="en",
    )


# ── Declining ────────────────────────────────────────────────────────────────

def test_declines_without_an_api_key(monkeypatch, mock_db):
    monkeypatch.setattr(unified_gemini_agent.settings, "GEMINI_API_KEY", "")
    assert _answer(db=mock_db) is None, (
        "With no key the stage must decline so the caller can answer "
        "deterministically. Returning a reply of its own is what made the old "
        "version of this test measure the legacy assistant."
    )


def test_declines_when_model_calls_are_suppressed(monkeypatch, mock_db):
    monkeypatch.setattr(unified_gemini_agent.settings, "GEMINI_API_KEY", "probe-key")
    monkeypatch.setattr(
        unified_gemini_agent.genai, "Client",
        lambda **kwargs: pytest.fail("A call was opened inside model_calls_suppressed()"),
    )
    with model_calls_suppressed():
        assert _answer(db=mock_db) is None


def test_declines_when_the_request_budget_is_spent(monkeypatch, mock_db):
    monkeypatch.setattr(unified_gemini_agent.settings, "GEMINI_API_KEY", "probe-key")
    monkeypatch.setattr(
        unified_gemini_agent.genai, "Client",
        lambda **kwargs: pytest.fail("A call was opened with no budget left"),
    )
    # Less than MINIMUM_USEFUL_BUDGET_SECONDS: an answer that would be cut off
    # is not worth the round trip.
    with request_budget(1.0):
        assert _answer(db=mock_db) is None


def test_declines_when_the_provider_fails(monkeypatch, mock_db):
    monkeypatch.setattr(unified_gemini_agent.settings, "GEMINI_API_KEY", "probe-key")

    def _boom(**kwargs):
        raise RuntimeError("503 UNAVAILABLE")

    monkeypatch.setattr(unified_gemini_agent.genai, "Client", _boom)
    assert _answer(db=mock_db) is None


def test_declines_when_the_model_returns_no_text(monkeypatch, mock_db):
    monkeypatch.setattr(unified_gemini_agent.settings, "GEMINI_API_KEY", "probe-key")
    monkeypatch.setattr(
        unified_gemini_agent.genai, "Client",
        lambda **kwargs: _StubClient([_Response(text=None)]),
    )
    assert _answer(db=mock_db) is None, (
        "An empty answer used to be reported as 'your request was processed "
        "successfully', which says nothing and sounds like something happened."
    )


# ── Answering ────────────────────────────────────────────────────────────────

def test_answers_in_the_language_of_the_message(monkeypatch, mock_db):
    monkeypatch.setattr(unified_gemini_agent.settings, "GEMINI_API_KEY", "probe-key")
    captured = {}

    def _client(**kwargs):
        stub = _StubClient([_Response(text="صافي الربح 1000")])
        captured["stub"] = stub
        return stub

    monkeypatch.setattr(unified_gemini_agent.genai, "Client", _client)
    reply = answer_with_tools(
        db=mock_db,
        company_id=1,
        user_role="accountant",
        message="كم صافي الأرباح والخسائر للشركة؟",
        page_context=PageContext(page="dashboard", route="/dashboard"),
        language="en",  # the message overrides the caller's preference
    )

    assert reply is not None
    assert reply.reply == "صافي الربح 1000"
    assert reply.intent == "unified_agent_response"
    instruction = captured["stub"].configs[0].system_instruction
    assert "Preferred Language: ar" in instruction
    assert "Company ID: 1" in instruction


def test_a_tool_call_runs_and_its_result_goes_back_to_the_model(monkeypatch, mock_db):
    monkeypatch.setattr(unified_gemini_agent.settings, "GEMINI_API_KEY", "probe-key")
    monkeypatch.setattr(
        unified_gemini_agent.genai, "Client",
        lambda **kwargs: _StubClient([
            _Response(function_calls=[_FunctionCall("get_profit_loss", {})]),
            _Response(text="Net profit is 1,500.00"),
        ]),
    )

    executed = {}

    def _execute(*, tool_name, args, db, company_id, user_role):
        executed.update(tool_name=tool_name, company_id=company_id, user_role=user_role, args=args)
        from app.modules.accounting.services.accounting_tool_registry import (
            ToolExecutionResult,
        )
        return ToolExecutionResult(data={"net_profit": 1500.0})

    with patch.object(
        unified_gemini_agent.AccountingToolRegistry, "execute_tool", staticmethod(_execute)
    ):
        reply = _answer(db=mock_db)

    assert reply is not None
    assert reply.reply == "Net profit is 1,500.00"
    assert executed["tool_name"] == "get_profit_loss"
    # The company comes from the caller, never from the model.
    assert executed["company_id"] == 1
    assert executed["user_role"] == "admin"
    assert reply.data_sources == ["database"]


def test_a_mutation_proposal_is_carried_out_to_the_reply(monkeypatch, mock_db):
    monkeypatch.setattr(unified_gemini_agent.settings, "GEMINI_API_KEY", "probe-key")
    monkeypatch.setattr(
        unified_gemini_agent.genai, "Client",
        lambda **kwargs: _StubClient([
            _Response(function_calls=[_FunctionCall(
                "propose_journal_entry",
                {"debit_account": "Rent Expense", "credit_account": "Cash",
                 "amount": 500, "description": "pay rent"},
            )]),
            _Response(text="Here is the draft."),
        ]),
    )

    rent, cash = MagicMock(), MagicMock()
    rent.id, rent.code, rent.name = 2, "5010", "Rent Expense"
    cash.id, cash.code, cash.name = 1, "1010", "Cash"
    mock_db.scalars.return_value.first.side_effect = [rent, cash]

    reply = _answer(message="Draft an entry to pay 500 rent from cash.", db=mock_db)

    assert reply is not None
    assert reply.suggested_action is not None
    assert reply.suggested_action.type == "create_journal_entry_draft"
    assert reply.suggested_action.requires_confirmation is True
    # Nothing was written: a proposal is a proposal until /confirm-action
    # re-validates it.
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()


def test_a_role_is_offered_only_the_tools_it_may_call(monkeypatch, mock_db):
    monkeypatch.setattr(unified_gemini_agent.settings, "GEMINI_API_KEY", "probe-key")
    seen = {}

    def _client(**kwargs):
        stub = _StubClient([_Response(text="ok")])
        seen["stub"] = stub
        return stub

    monkeypatch.setattr(unified_gemini_agent.genai, "Client", _client)
    _answer(role="viewer", db=mock_db)

    declared = {
        declaration.name
        for tool in seen["stub"].configs[0].tools
        for declaration in (tool.function_declarations or [])
    }
    assert "get_profit_loss" in declared
    assert "get_company_users" not in declared, (
        "The model cannot call what it is not offered, and a viewer may not "
        "read company users."
    )
    assert "propose_journal_entry" not in declared
