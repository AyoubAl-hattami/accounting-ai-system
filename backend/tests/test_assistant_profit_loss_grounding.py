"""Focused Phase 1 tests for deterministic Profit and Loss grounding.

These tests are intentionally not executed by the implementation task.
"""
from datetime import date
from decimal import Decimal

from app.modules.accounting.schemas.gemini_assistant_schemas import (
    ProfitAndLossGrounding,
    ProfitAndLossMetrics,
)
from app.modules.accounting.services.gemini_assistant_service import (
    _build_profit_loss_grounding,
    _grounding_failure_reply,
)


def _data():
    return {
        "total_revenue": Decimal("5000.00"),
        "total_expenses": Decimal("2800.00"),
        "net_profit": Decimal("2200.00"),
    }


def test_grounding_uses_decimal_strings_and_allowlisted_report():
    result = _build_profit_loss_grounding(
        _data(), 999, date(2026, 7, 1), date(2026, 7, 31), "2026-07-01 – 2026-07-31"
    )
    assert result.status == "grounded"
    assert result.kind == "profit_and_loss"
    assert result.metrics == ProfitAndLossMetrics(
        revenue="5000.00", expenses="2800.00", net_profit="2200.00"
    )
    assert result.reference.report == "profit_and_loss"
    assert not hasattr(result, "company_id")
    assert not hasattr(result, "url")


def test_grounding_failure_contains_no_estimate_or_exception():
    result = _build_profit_loss_grounding({"error": "private failure"}, 1, None, None, "all available data")
    assert result == ProfitAndLossGrounding(status="unavailable", kind="profit_and_loss")
    assert "private failure" not in _grounding_failure_reply("en")
    assert "estimate" in _grounding_failure_reply("en")


def test_historical_grounding_schema_is_optional():
    assert ProfitAndLossGrounding(status="unavailable", kind="profit_and_loss").metrics is None