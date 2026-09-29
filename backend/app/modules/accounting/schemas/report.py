from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class TrialBalanceLine(BaseModel):
    account_id: int
    account_code: str
    account_name: str
    account_type: str

    debit_total: Decimal
    credit_total: Decimal

    debit_balance: Decimal
    credit_balance: Decimal


class TrialBalanceRead(BaseModel):
    company_id: int
    # The one unit every figure in this report is in. A company that keeps
    # riyal and dollar accounts gets one report per currency, never a sum of both.
    currency: str | None = None
    as_of_date: date | None = None

    total_debit: Decimal
    total_credit: Decimal

    total_debit_balance: Decimal
    total_credit_balance: Decimal

    is_balanced: bool

    lines: list[TrialBalanceLine]


class ProfitAndLossLine(BaseModel):
    account_id: int
    account_code: str
    account_name: str
    account_type: str

    amount: Decimal


class ProfitAndLossRead(BaseModel):
    company_id: int
    # The one unit every figure in this report is in. A company that keeps
    # riyal and dollar accounts gets one report per currency, never a sum of both.
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    total_income: Decimal
    total_expenses: Decimal

    net_profit: Decimal

    income_lines: list[ProfitAndLossLine]
    expense_lines: list[ProfitAndLossLine]
class BalanceSheetLine(BaseModel):
    account_id: int
    account_code: str
    account_name: str
    account_type: str

    amount: Decimal


class BalanceSheetRead(BaseModel):
    company_id: int
    # The one unit every figure in this report is in. A company that keeps
    # riyal and dollar accounts gets one report per currency, never a sum of both.
    currency: str | None = None
    as_of_date: date | None = None

    total_assets: Decimal
    total_liabilities: Decimal
    equity_accounts_total: Decimal
    prior_year_earnings: Decimal
    retained_earnings: Decimal
    current_year_earnings: Decimal
    total_equity: Decimal

    total_liabilities_and_equity: Decimal
    is_balanced: bool

    asset_lines: list[BalanceSheetLine]
    liability_lines: list[BalanceSheetLine]
    equity_lines: list[BalanceSheetLine]
class AccountLedgerLine(BaseModel):
    journal_entry_id: int
    entry_no: str
    entry_date: date

    line_no: int
    description: str | None = None

    debit: Decimal
    credit: Decimal
    running_balance: Decimal


class AccountLedgerRead(BaseModel):
    company_id: int
    # The one unit every figure in this report is in. A company that keeps
    # riyal and dollar accounts gets one report per currency, never a sum of both.
    currency: str | None = None

    account_id: int
    account_code: str
    account_name: str
    account_type: str

    start_date: date | None = None
    end_date: date | None = None

    opening_balance: Decimal
    closing_balance: Decimal

    lines: list[AccountLedgerLine]

    # Lines in the whole window, against which `lines` may be a single page.
    total_lines: int = 0
    line_skip: int | None = None
    line_limit: int | None = None
class GeneralLedgerRead(BaseModel):
    company_id: int
    # The one unit every figure in this report is in. A company that keeps
    # riyal and dollar accounts gets one report per currency, never a sum of both.
    currency: str | None = None

    start_date: date | None = None
    end_date: date | None = None

    accounts: list[AccountLedgerRead]

    # Accounts in the company, against which `accounts` may be a single page.
    total_accounts: int = 0
    account_skip: int | None = None
    account_limit: int | None = None


class AgingItem(BaseModel):
    partner_id: int
    partner_code: str
    partner_name: str
    invoice_id: int
    invoice_no: str
    invoice_date: date
    due_date: date
    original_amount: Decimal
    paid_amount: Decimal
    credited_amount: Decimal = Decimal("0.00")
    outstanding_amount: Decimal
    days_overdue: int
    bucket: str
    currency: str


class AgingTotals(BaseModel):
    total_current: Decimal
    total_1_30: Decimal
    total_31_60: Decimal
    total_61_90: Decimal
    total_91_120: Decimal
    total_120_plus: Decimal
    total_outstanding: Decimal


class AgingReportRead(BaseModel):
    company_id: int
    report_type: str  # "ar" or "ap"
    as_of_date: date
    currency: str
    items: list[AgingItem]
    totals: AgingTotals


class StatementTransactionItem(BaseModel):
    date: date
    type: str  # "invoice" or "payment"
    document_no: str
    reference: str | None = None
    description: str | None = None
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


class PartnerStatementRead(BaseModel):
    company_id: int
    partner_id: int
    partner_name: str
    partner_code: str
    partner_type: str  # "customer", "vendor", or "both"
    currency: str
    date_from: date
    date_to: date
    opening_balance: Decimal
    transactions: list[StatementTransactionItem]
    closing_balance: Decimal
    total_debit: Decimal
    total_credit: Decimal