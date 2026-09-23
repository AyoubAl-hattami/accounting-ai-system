"""Grounding cards built from report DTOs, for whoever has the DTO.

The deterministic path builds its cards from dicts it made moments earlier,
or inline inside the reply function, entangled with the sentence. Neither is
reusable, and the tool path has the DTO in its hand -- the object the report
service returned -- at the moment it flattens it for the model.

So the card is built there, from that object, in the same call. The model
receives the flattened dict and never sees the card; the card is attached
server-side after the model has finished, and only if the gate vouches for
what the model wrote. That is the whole guarantee: the figures in the card
cannot be the model's, because the model was never given them to edit.

This module holds one builder today. The other four kinds live inline in
gemini_assistant_service._structured_report_reply and move here one at a
time, each with its output asserted byte-identical first.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.application.reports.dto import ProfitAndLossRead
from app.modules.accounting.schemas.gemini_assistant_schemas import (
    ProfitAndLossGrounding,
    ProfitAndLossMetrics,
    ProfitAndLossPeriod,
    ProfitAndLossReference,
)

# What a period with no dates is called, matching the deterministic path.
ALL_AVAILABLE_DATA = "All available data"


def report_amount(value: Decimal) -> str:
    """Two decimal places, as a string, the way every card writes money.

    A second implementation of gemini_assistant_service._report_amount, and
    deliberately not an import of it: this module is reached from the tool
    registry, and importing the 4,000-line assistant service to format a
    Decimal would drag the whole dispatcher behind it. The duplication is
    covered by a test that compares the two across a range of values, so
    drift fails rather than quietly producing two spellings of one figure.
    """
    return Decimal(value).quantize(Decimal("0.01")).to_eng_string()


def _period(start_date: date | None, end_date: date | None) -> ProfitAndLossPeriod:
    if start_date is None and end_date is None:
        label = ALL_AVAILABLE_DATA
    else:
        label = f"{start_date or 'start'} to {end_date or 'today'}"
    return ProfitAndLossPeriod(
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        label=label,
    )


def profit_and_loss_grounding(
    report: ProfitAndLossRead,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    requested_metric: str = "net_profit",
) -> ProfitAndLossGrounding:
    """The card for a profit and loss report, from the report itself.

    ``requested_metric`` only decides which row the card highlights. It
    defaults to net profit rather than being guessed from the question: a
    wrong highlight is cosmetic, and a guess that reads the user's words
    would put model-adjacent inference inside the one structure that exists
    to be free of it.
    """
    filters: dict[str, str] = {}
    if start_date is not None:
        filters["start_date"] = start_date.isoformat()
    if end_date is not None:
        filters["end_date"] = end_date.isoformat()

    return ProfitAndLossGrounding(
        status="grounded",
        kind="profit_and_loss",
        requested_metric=(
            requested_metric
            if requested_metric in {"revenue", "expenses", "net_profit"}
            else "net_profit"
        ),
        period=_period(start_date, end_date),
        metrics=ProfitAndLossMetrics(
            revenue=report_amount(report.total_income),
            expenses=report_amount(report.total_expenses),
            net_profit=report_amount(report.net_profit),
        ),
        reference=ProfitAndLossReference(
            type="report", report="profit_and_loss", filters=filters
        ),
    )
