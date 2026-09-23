"""The first model-path card: built from the report, attached only if vouched.

get_profit_loss is the reference for the other report tools. It does three
things and each is asserted here:

  - flattens the report for the model, as before;
  - builds the card from the SAME DTO, in the same call;
  - hands both back, so the agent can attach the card the model never saw.

The guarantee is structural. The model is given `data`; the card is built
from the object behind `data` and attached after the model has finished. A
figure in the card cannot be one the model wrote -- and whether the model's
SENTENCE deserves that card is the gate's question, which is why the last
tests here are about refusal.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.application.reports.dto import ProfitAndLossLine, ProfitAndLossRead
from app.modules.accounting.schemas.gemini_assistant_schemas import PageContext
from app.modules.accounting.services import accounting_tool_registry as registry
from app.modules.accounting.services import gemini_assistant_service as service
from app.modules.accounting.services import unified_gemini_agent
from app.modules.accounting.services.report_grounding import (
    profit_and_loss_grounding,
    report_amount,
)

REPORT = ProfitAndLossRead(
    company_id=1,
    start_date=date(2026, 1, 1),
    end_date=date(2026, 1, 31),
    total_income=Decimal("4000.00"),
    total_expenses=Decimal("1500.00"),
    net_profit=Decimal("2500.00"),
    income_lines=[ProfitAndLossLine(account_id=1, account_code="4100", account_name="Sales", account_type="income", amount=Decimal("4000.00"))],
    expense_lines=[ProfitAndLossLine(account_id=2, account_code="5100", account_name="Rent", account_type="expense", amount=Decimal("1500.00"))],
    currency="USD",
)


# ── The card is the report ───────────────────────────────────────────────────

def test_the_card_carries_the_reports_own_figures():
    grounding = profit_and_loss_grounding(
        REPORT, start_date=REPORT.start_date, end_date=REPORT.end_date
    )

    assert grounding.status == "grounded"
    assert grounding.metrics.revenue == report_amount(REPORT.total_income)
    assert grounding.metrics.expenses == report_amount(REPORT.total_expenses)
    assert grounding.metrics.net_profit == report_amount(REPORT.net_profit)
    assert grounding.period.start_date == "2026-01-01"
    assert grounding.reference.filters == {"start_date": "2026-01-01", "end_date": "2026-01-31"}


def test_a_period_with_no_dates_says_so():
    grounding = profit_and_loss_grounding(REPORT)
    assert grounding.period.label == "All available data"
    assert grounding.reference.filters == {}


def test_the_two_money_formatters_agree():
    """report_amount duplicates the assistant service's formatter on purpose --
    importing a 4,000-line dispatcher to format a Decimal would drag the whole
    thing into the tool registry. Duplication is fine; drift is not."""
    for value in ("0", "0.005", "1500", "1500.004", "-2500.5", "31337.129", "1e3"):
        assert report_amount(Decimal(value)) == service._report_amount(Decimal(value))


def test_the_tool_returns_both_halves():
    with patch.object(registry, "get_profit_and_loss", return_value=REPORT):
        result = registry.tool_get_profit_loss(db=MagicMock(), company_id=1)

    assert result.data["total_revenue"] == 4000.0
    assert result.grounding is not None
    assert result.grounding.metrics.net_profit == "2500.00"


def test_the_model_facing_payload_did_not_change_shape():
    """The dict the model reads is the one it read before; only the envelope
    around it gained a field."""
    with patch.object(registry, "get_profit_and_loss", return_value=REPORT):
        result = registry.tool_get_profit_loss(db=MagicMock(), company_id=1)

    assert set(result.data) == {
        "total_revenue", "total_expenses", "net_profit", "currency",
        "revenue_lines", "expense_lines",
    }


# ── The agent attaches it only behind the gate ───────────────────────────────

class _Part:
    def __init__(self, text=None):
        self.text = text


class _Content:
    def __init__(self, parts):
        self.parts, self.role = parts, "model"


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
        self.name, self.args = name, args


def _answer(monkeypatch, model_text, tool_results):
    """Run the agent with a stub model that calls one tool and then speaks."""
    monkeypatch.setattr(unified_gemini_agent.settings, "GEMINI_API_KEY", "probe-key")

    class _Client:
        def __init__(self, **kwargs):
            self.models = self
            self._responses = [
                _Response(function_calls=[_FunctionCall("get_profit_loss", {})]),
                _Response(text=model_text),
            ]

        def generate_content(self, *, model, contents, config):
            return self._responses.pop(0)

    monkeypatch.setattr(unified_gemini_agent.genai, "Client", _Client)

    results = iter(tool_results)

    def _execute(*, tool_name, args, db, company_id, user_role):
        return next(results)

    with patch.object(
        unified_gemini_agent.AccountingToolRegistry, "execute_tool", staticmethod(_execute)
    ):
        return unified_gemini_agent.answer_with_tools(
            db=MagicMock(),
            company_id=1,
            user_role="admin",
            message="What is our net profit?",
            page_context=PageContext(page="dashboard", route="/dashboard"),
            language="en",
        )


def _grounded_result():
    return registry.ToolExecutionResult(
        data={"net_profit": 2500.0},
        grounding=profit_and_loss_grounding(REPORT, start_date=REPORT.start_date, end_date=REPORT.end_date),
    )


def test_a_quoted_figure_earns_the_card(monkeypatch):
    reply = _answer(
        monkeypatch,
        "Revenue was 4000.00, expenses 1500.00, so net profit is 2500.00.",
        [_grounded_result()],
    )

    assert reply is not None
    assert reply.grounding is not None
    assert reply.grounding.kind == "profit_and_loss"
    assert reply.grounding.metrics.net_profit == "2500.00"
    assert reply.confidence == "high"


def test_an_invented_figure_loses_the_card(monkeypatch):
    reply = _answer(monkeypatch, "Net profit is 9,900.00.", [_grounded_result()])

    assert reply is not None
    assert reply.grounding is None, (
        "The model stated a figure the report does not contain; the badge "
        "must not appear beside it."
    )
    assert reply.confidence == "medium"
    assert "9,900.00" in reply.reply, "The answer is still delivered, without the claim."


def test_a_tool_without_a_card_leaves_the_reply_unbadged(monkeypatch):
    reply = _answer(
        monkeypatch,
        "You have 5 users.",
        [registry.ToolExecutionResult(data={"users": 5})],
    )

    assert reply is not None
    assert reply.grounding is None
    assert reply.confidence == "medium"


def test_the_card_is_never_sent_to_the_model(monkeypatch):
    """The structural half of the guarantee: what the model receives contains
    the flattened figures and no card."""
    monkeypatch.setattr(unified_gemini_agent.settings, "GEMINI_API_KEY", "probe-key")
    seen: list = []

    class _Client:
        def __init__(self, **kwargs):
            self.models = self
            self._responses = [
                _Response(function_calls=[_FunctionCall("get_profit_loss", {})]),
                _Response(text="Net profit is 2500.00."),
            ]

        def generate_content(self, *, model, contents, config):
            seen.append(list(contents))
            return self._responses.pop(0)

    monkeypatch.setattr(unified_gemini_agent.genai, "Client", _Client)

    with patch.object(
        unified_gemini_agent.AccountingToolRegistry,
        "execute_tool",
        staticmethod(lambda **kwargs: _grounded_result()),
    ):
        unified_gemini_agent.answer_with_tools(
            db=MagicMock(),
            company_id=1,
            user_role="admin",
            message="What is our net profit?",
            page_context=PageContext(page="dashboard", route="/dashboard"),
            language="en",
        )

    everything_sent = repr(seen)
    assert "profit_and_loss" not in everything_sent or "kind" not in everything_sent, (
        "A grounding object reached the model."
    )
    assert "requested_metric" not in everything_sent
