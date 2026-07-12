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

    account_id: int
    account_code: str
    account_name: str
    account_type: str

    start_date: date | None = None
    end_date: date | None = None

    opening_balance: Decimal
    closing_balance: Decimal

    lines: list[AccountLedgerLine]
class GeneralLedgerRead(BaseModel):
    company_id: int

    start_date: date | None = None
    end_date: date | None = None

    accounts: list[AccountLedgerRead]