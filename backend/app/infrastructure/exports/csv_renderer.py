"""CSV rendering adapter for accounting reports.

Converts application report DTOs into UTF-8 CSV text (with BOM for Excel and
Arabic text compatibility).  All accounting logic is in the application layer;
this module only handles column layout and string formatting.

Implements ``ReportCsvRenderer`` from ``application.reports.export_ports``.
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal

from app.application.reports.dto import (
    AccountLedgerRead,
    BalanceSheetRead,
    GeneralLedgerRead,
    ProfitAndLossRead,
    TrialBalanceRead,
)

# UTF-8 BOM for Excel and Arabic text compatibility
_UTF8_BOM = "﻿"


def _fmt(value: Decimal) -> str:
    return f"{value:.2f}"


# Characters a spreadsheet treats as the start of a formula.  csv quoting does
# not help: it is a transport encoding, so `=HYPERLINK("http://x","y")` is
# quoted on the wire and still arrives in the cell as a formula.
_FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")


def _safe(value: str | None) -> str:
    """Neutralise a free-text cell that would otherwise be read as a formula.

    Applied only to operator-supplied text — account codes and names, entry
    numbers, line descriptions.  Never to ``_fmt`` output: a legitimate negative
    amount renders as ``-100.00`` and prefixing it would break the cell's
    number parsing for the sake of a value no spreadsheet evaluates anyway.
    """
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_TRIGGERS) else text


def trial_balance_to_csv(report: TrialBalanceRead) -> str:
    """Convert a trial balance report DTO to CSV text."""
    buf = io.StringIO()
    buf.write(_UTF8_BOM)
    writer = csv.writer(buf)

    writer.writerow(["Account Code", "Account Name", "Account Type", "Debit", "Credit"])
    for line in report.lines:
        writer.writerow([
            _safe(line.account_code),
            _safe(line.account_name),
            line.account_type,
            _fmt(line.debit_balance),
            _fmt(line.credit_balance),
        ])
    writer.writerow([])
    writer.writerow([
        "", "Totals", "",
        _fmt(report.total_debit_balance),
        _fmt(report.total_credit_balance),
    ])
    return buf.getvalue()


def profit_and_loss_to_csv(report: ProfitAndLossRead) -> str:
    """Convert a profit & loss report DTO to CSV text."""
    buf = io.StringIO()
    buf.write(_UTF8_BOM)
    writer = csv.writer(buf)

    writer.writerow(["Section", "Account Code", "Account Name", "Amount"])
    for line in report.income_lines:
        writer.writerow(["Income", _safe(line.account_code), _safe(line.account_name), _fmt(line.amount)])
    writer.writerow(["", "", "Total Revenue", _fmt(report.total_income)])
    writer.writerow([])
    for line in report.expense_lines:
        writer.writerow(["Expenses", _safe(line.account_code), _safe(line.account_name), _fmt(line.amount)])
    writer.writerow(["", "", "Total Expenses", _fmt(report.total_expenses)])
    writer.writerow([])
    writer.writerow(["", "", "Net Income", _fmt(report.net_profit)])
    return buf.getvalue()


def balance_sheet_to_csv(report: BalanceSheetRead) -> str:
    """Convert a balance sheet report DTO to CSV text."""
    buf = io.StringIO()
    buf.write(_UTF8_BOM)
    writer = csv.writer(buf)

    writer.writerow(["Section", "Account Code", "Account Name", "Amount"])
    for line in report.asset_lines:
        writer.writerow(["Assets", _safe(line.account_code), _safe(line.account_name), _fmt(line.amount)])
    writer.writerow(["", "", "Total Assets", _fmt(report.total_assets)])
    writer.writerow([])
    for line in report.liability_lines:
        writer.writerow(["Liabilities", _safe(line.account_code), _safe(line.account_name), _fmt(line.amount)])
    writer.writerow(["", "", "Total Liabilities", _fmt(report.total_liabilities)])
    writer.writerow([])
    for line in report.equity_lines:
        writer.writerow(["Equity", _safe(line.account_code), _safe(line.account_name), _fmt(line.amount)])
    writer.writerow(["", "", "Equity Accounts Total", _fmt(report.equity_accounts_total)])
    writer.writerow([
        "", "", "Retained Earnings / Prior-Year Earnings",
        _fmt(report.retained_earnings),
    ])
    writer.writerow(["", "", "Current-Year Earnings", _fmt(report.current_year_earnings)])
    writer.writerow(["", "", "Total Equity", _fmt(report.total_equity)])
    writer.writerow([])
    writer.writerow([
        "", "", "Total Liabilities & Equity",
        _fmt(report.total_liabilities_and_equity),
    ])
    return buf.getvalue()


def account_ledger_to_csv(report: AccountLedgerRead) -> str:
    """Convert an account ledger report DTO to CSV text."""
    buf = io.StringIO()
    buf.write(_UTF8_BOM)
    writer = csv.writer(buf)

    writer.writerow([
        f"Account: {report.account_code} - {report.account_name} ({report.account_type})",
    ])
    writer.writerow([])
    writer.writerow(["Date", "Entry No", "Description", "Debit", "Credit", "Balance"])
    writer.writerow(["", "", "Opening Balance", "", "", _fmt(report.opening_balance)])
    for line in report.lines:
        writer.writerow([
            str(line.entry_date),
            _safe(line.entry_no),
            _safe(line.description),
            _fmt(line.debit),
            _fmt(line.credit),
            _fmt(line.running_balance),
        ])
    writer.writerow(["", "", "Closing Balance", "", "", _fmt(report.closing_balance)])
    return buf.getvalue()


def general_ledger_to_csv(report: GeneralLedgerRead) -> str:
    """Convert a general ledger report DTO to CSV text."""
    buf = io.StringIO()
    buf.write(_UTF8_BOM)
    writer = csv.writer(buf)

    writer.writerow([
        "Account Code", "Account Name", "Date", "Entry No",
        "Description", "Debit", "Credit", "Balance",
    ])
    for account in report.accounts:
        writer.writerow([
            _safe(account.account_code), _safe(account.account_name), "", "",
            "Opening Balance", "", "", _fmt(account.opening_balance),
        ])
        for line in account.lines:
            writer.writerow([
                _safe(account.account_code), _safe(account.account_name),
                str(line.entry_date), _safe(line.entry_no),
                _safe(line.description),
                _fmt(line.debit), _fmt(line.credit), _fmt(line.running_balance),
            ])
        writer.writerow([
            _safe(account.account_code), _safe(account.account_name), "", "",
            "Closing Balance", "", "", _fmt(account.closing_balance),
        ])
    return buf.getvalue()
