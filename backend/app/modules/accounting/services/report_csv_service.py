"""
CSV formatting utilities for accounting reports.

Converts report data structures (from report_service) into CSV strings.
All accounting logic is delegated to report_service; this module only
handles column layout and string formatting.

UTF-8 BOM is prepended for Excel and Arabic text compatibility.
"""

import csv
import io
from decimal import Decimal

from app.modules.accounting.schemas.report import (
    TrialBalanceRead,
    ProfitAndLossRead,
    BalanceSheetRead,
    AccountLedgerRead,
    GeneralLedgerRead,
)

# UTF-8 BOM for Excel compatibility
UTF8_BOM = "\ufeff"


def _fmt(value: Decimal) -> str:
    """Format a Decimal to a plain string with two decimal places."""
    return f"{value:.2f}"


def trial_balance_to_csv(report: TrialBalanceRead) -> str:
    """Convert a trial balance report to CSV text."""
    buf = io.StringIO()
    buf.write(UTF8_BOM)
    writer = csv.writer(buf)

    writer.writerow(["Account Code", "Account Name", "Account Type", "Debit", "Credit"])

    for line in report.lines:
        writer.writerow([
            line.account_code,
            line.account_name,
            line.account_type,
            _fmt(line.debit_balance),
            _fmt(line.credit_balance),
        ])

    writer.writerow([])
    writer.writerow(["", "Totals", "", _fmt(report.total_debit_balance), _fmt(report.total_credit_balance)])

    return buf.getvalue()


def profit_and_loss_to_csv(report: ProfitAndLossRead) -> str:
    """Convert a profit & loss report to CSV text."""
    buf = io.StringIO()
    buf.write(UTF8_BOM)
    writer = csv.writer(buf)

    writer.writerow(["Section", "Account Code", "Account Name", "Amount"])

    for line in report.income_lines:
        writer.writerow(["Income", line.account_code, line.account_name, _fmt(line.amount)])

    writer.writerow(["", "", "Total Revenue", _fmt(report.total_income)])
    writer.writerow([])

    for line in report.expense_lines:
        writer.writerow(["Expenses", line.account_code, line.account_name, _fmt(line.amount)])

    writer.writerow(["", "", "Total Expenses", _fmt(report.total_expenses)])
    writer.writerow([])
    writer.writerow(["", "", "Net Income", _fmt(report.net_profit)])

    return buf.getvalue()


def balance_sheet_to_csv(report: BalanceSheetRead) -> str:
    """Convert a balance sheet report to CSV text."""
    buf = io.StringIO()
    buf.write(UTF8_BOM)
    writer = csv.writer(buf)

    writer.writerow(["Section", "Account Code", "Account Name", "Amount"])

    for line in report.asset_lines:
        writer.writerow(["Assets", line.account_code, line.account_name, _fmt(line.amount)])

    writer.writerow(["", "", "Total Assets", _fmt(report.total_assets)])
    writer.writerow([])

    for line in report.liability_lines:
        writer.writerow(["Liabilities", line.account_code, line.account_name, _fmt(line.amount)])

    writer.writerow(["", "", "Total Liabilities", _fmt(report.total_liabilities)])
    writer.writerow([])

    for line in report.equity_lines:
        writer.writerow(["Equity", line.account_code, line.account_name, _fmt(line.amount)])

    writer.writerow(["", "", "Equity Accounts Total", _fmt(report.equity_accounts_total)])
    writer.writerow(["", "", "Retained Earnings / Prior-Year Earnings", _fmt(report.retained_earnings)])
    writer.writerow(["", "", "Current-Year Earnings", _fmt(report.current_year_earnings)])
    writer.writerow(["", "", "Total Equity", _fmt(report.total_equity)])
    writer.writerow([])
    writer.writerow(["", "", "Total Liabilities & Equity", _fmt(report.total_liabilities_and_equity)])

    return buf.getvalue()


def account_ledger_to_csv(report: AccountLedgerRead) -> str:
    """Convert an account ledger report to CSV text."""
    buf = io.StringIO()
    buf.write(UTF8_BOM)
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
            line.entry_no,
            line.description or "",
            _fmt(line.debit),
            _fmt(line.credit),
            _fmt(line.running_balance),
        ])

    writer.writerow(["", "", "Closing Balance", "", "", _fmt(report.closing_balance)])

    return buf.getvalue()


def general_ledger_to_csv(report: GeneralLedgerRead) -> str:
    """Convert a general ledger report to CSV text."""
    buf = io.StringIO()
    buf.write(UTF8_BOM)
    writer = csv.writer(buf)

    writer.writerow([
        "Account Code", "Account Name", "Date", "Entry No",
        "Description", "Debit", "Credit", "Balance",
    ])

    for account in report.accounts:
        # Opening balance row
        writer.writerow([
            account.account_code,
            account.account_name,
            "",
            "",
            "Opening Balance",
            "",
            "",
            _fmt(account.opening_balance),
        ])

        for line in account.lines:
            writer.writerow([
                account.account_code,
                account.account_name,
                str(line.entry_date),
                line.entry_no,
                line.description or "",
                _fmt(line.debit),
                _fmt(line.credit),
                _fmt(line.running_balance),
            ])

        # Closing balance row
        writer.writerow([
            account.account_code,
            account.account_name,
            "",
            "",
            "Closing Balance",
            "",
            "",
            _fmt(account.closing_balance),
        ])

    return buf.getvalue()
