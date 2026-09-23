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

The kinds move here one at a time out of
gemini_assistant_service._structured_report_reply, each with its output
asserted byte-identical first -- tests/test_structured_grounding_parity.py
holds a card captured from the code before its builder was extracted.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.application.reports.dto import (
    BalanceSheetRead,
    GeneralLedgerRead,
    ProfitAndLossRead,
    TrialBalanceRead,
)
from app.modules.accounting.schemas.gemini_assistant_schemas import (
    BalanceSheetGrounding,
    GeneralLedgerGrounding,
    ReportSummary,
    ProfitAndLossGrounding,
    ProfitAndLossMetrics,
    ProfitAndLossPeriod,
    ProfitAndLossReference,
    ReportPeriod,
    ReportReference,
    TrialBalanceGrounding,
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


BALANCE_SHEET_ACCOUNTS_SHOWN = 50


def balance_sheet_grounding(
    report: BalanceSheetRead,
    *,
    requested_metric: str = "assets",
) -> BalanceSheetGrounding:
    """The card for a balance sheet, from the report itself.

    Moved verbatim out of _structured_report_reply: the metric names, the
    section order, the 50-account cap and the "As of <date>" label are what
    that code produced, and the parity test compares a card built here against
    one captured before the move.
    """
    as_of = report.as_of_date
    metrics: dict[str, str | bool] = {
        "total_assets": report_amount(report.total_assets),
        "total_liabilities": report_amount(report.total_liabilities),
        "total_equity": report_amount(report.total_equity),
        "current_year_earnings": report_amount(report.current_year_earnings),
        "prior_year_earnings": report_amount(report.prior_year_earnings),
        "liabilities_and_equity": report_amount(report.total_liabilities_and_equity),
        "difference": report_amount(report.total_assets - report.total_liabilities_and_equity),
        "is_balanced": report.total_assets == report.total_liabilities_and_equity,
    }
    sections = [
        {
            "section": name,
            "total": report_amount(total),
            "accounts": [
                {
                    "account_id": line.account_id,
                    "account_code": line.account_code,
                    "account_name": line.account_name,
                    "balance": report_amount(line.amount),
                }
                for line in lines[:BALANCE_SHEET_ACCOUNTS_SHOWN]
            ],
        }
        for name, total, lines in (
            ("assets", report.total_assets, report.asset_lines),
            ("liabilities", report.total_liabilities, report.liability_lines),
            ("equity", report.total_equity, report.equity_lines),
        )
    ]
    return BalanceSheetGrounding(
        status="grounded",
        kind="balance_sheet",
        requested_metric=requested_metric,
        period=ReportPeriod(
            as_of_date=as_of.isoformat() if as_of else None,
            label=f"As of {as_of}",
        ),
        metrics=metrics,
        sections=sections,
        reference=ReportReference(
            type="report",
            report="balance_sheet",
            filters={"as_of_date": as_of.isoformat() if as_of else None},
        ),
    )


TRIAL_BALANCE_ACCOUNTS_SHOWN = 50


def trial_balance_grounding(
    report: TrialBalanceRead,
    *,
    requested_metric: str | None = None,
    label: str | None = None,
) -> TrialBalanceGrounding:
    """The card for a trial balance, from the report itself.

    Moved verbatim out of _structured_report_reply, including the difference
    it computes rather than reads -- TrialBalanceRead carries is_balanced but
    not the difference, so the card has always subtracted the two totals
    itself. ``label`` is the period wording the handler derived from the
    question; without one the card falls back to the same "As of <date>" or
    "All available data" the handler falls back to.
    """
    difference = report.total_debit - report.total_credit
    lines = [
        {
            "account_id": line.account_id,
            "account_code": line.account_code,
            "account_name": line.account_name,
            "account_type": line.account_type,
            "debit_balance": report_amount(line.debit_balance),
            "credit_balance": report_amount(line.credit_balance),
            "net_balance": report_amount(line.debit_balance - line.credit_balance),
        }
        for line in report.lines[:TRIAL_BALANCE_ACCOUNTS_SHOWN]
    ]
    return TrialBalanceGrounding(
        status="grounded",
        kind="trial_balance",
        requested_metric=requested_metric,
        period=ReportPeriod(
            as_of_date=report.as_of_date.isoformat() if report.as_of_date else None,
            label=label
            or (f"As of {report.as_of_date}" if report.as_of_date else ALL_AVAILABLE_DATA),
        ),
        metrics={
            "total_debit": report_amount(report.total_debit),
            "total_credit": report_amount(report.total_credit),
            "difference": report_amount(difference),
            "is_balanced": difference == Decimal("0"),
        },
        accounts=lines,
        summary=ReportSummary(
            total_accounts=len(report.lines),
            returned_accounts=len(lines),
            has_more=len(report.lines) > len(lines),
        ),
        reference=ReportReference(
            type="report",
            report="trial_balance",
            filters={"end_date": report.as_of_date.isoformat() if report.as_of_date else None},
        ),
    )


GENERAL_LEDGER_ACCOUNTS_SHOWN = 20


def _report_period_for(
    start_date: date | None, end_date: date | None, label: str | None
) -> ReportPeriod:
    return ReportPeriod(
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        label=label or ALL_AVAILABLE_DATA,
    )


def account_totals(account) -> tuple[Decimal, Decimal]:
    """Debit and credit totals for one ledger account, summed from its lines.

    AccountLedgerRead carries opening and closing balances and no totals, so
    every caller that wants them sums the lines. Two callers did it inline;
    this is the one place that does it now.
    """
    debit = sum((line.debit for line in account.lines), Decimal("0.00"))
    credit = sum((line.credit for line in account.lines), Decimal("0.00"))
    return debit, credit


def general_ledger_grounding(
    report: GeneralLedgerRead,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    requested_metric: str | None = None,
    label: str | None = None,
) -> GeneralLedgerGrounding:
    """The card for a general ledger, from the report itself.

    Moved verbatim out of _structured_report_reply, including two details
    that look like mistakes and are not: the 20-account cap, and
    total_accounts counting the accounts in the REPORT rather than
    report.total_accounts, which [D3] added for the paginated case. Changing
    either would change the card, and this commit moves it.
    """
    accounts = report.accounts[:GENERAL_LEDGER_ACCOUNTS_SHOWN]
    rows = []
    for account in accounts:
        debit, credit = account_totals(account)
        rows.append(
            {
                "account_id": account.account_id,
                "account_code": account.account_code,
                "account_name": account.account_name,
                "account_type": account.account_type,
                "opening_balance": report_amount(account.opening_balance),
                "total_debit": report_amount(debit),
                "total_credit": report_amount(credit),
                "closing_balance": report_amount(account.closing_balance),
                "entry_count": len(account.lines),
            }
        )
    return GeneralLedgerGrounding(
        status="grounded",
        kind="general_ledger",
        requested_metric=requested_metric,
        period=_report_period_for(start_date, end_date, label),
        accounts=rows,
        summary=ReportSummary(
            total_accounts=len(report.accounts),
            returned_accounts=len(rows),
            has_more=len(report.accounts) > len(rows),
        ),
        reference=ReportReference(
            type="report",
            report="general_ledger",
            filters={
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
        ),
    )
