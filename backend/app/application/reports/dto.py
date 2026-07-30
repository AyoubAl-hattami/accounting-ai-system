"""Framework-neutral report queries and result DTOs."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TrialBalanceQuery:
    company_id: int
    as_of_date: date | None = None


@dataclass(frozen=True, slots=True)
class ProfitAndLossQuery:
    company_id: int
    start_date: date | None = None
    end_date: date | None = None


@dataclass(frozen=True, slots=True)
class BalanceSheetQuery:
    company_id: int
    as_of_date: date | None = None


@dataclass(frozen=True, slots=True)
class AccountLedgerQuery:
    company_id: int
    account_id: int
    start_date: date | None = None
    end_date: date | None = None


@dataclass(frozen=True, slots=True)
class GeneralLedgerQuery:
    company_id: int
    start_date: date | None = None
    end_date: date | None = None


@dataclass(frozen=True, slots=True)
class TrialBalanceLine:
    account_id: int
    account_code: str
    account_name: str
    account_type: str
    debit_total: Decimal
    credit_total: Decimal
    debit_balance: Decimal
    credit_balance: Decimal


@dataclass(frozen=True, slots=True)
class TrialBalanceRead:
    company_id: int
    as_of_date: date | None
    total_debit: Decimal
    total_credit: Decimal
    total_debit_balance: Decimal
    total_credit_balance: Decimal
    is_balanced: bool
    lines: list[TrialBalanceLine]


@dataclass(frozen=True, slots=True)
class ProfitAndLossLine:
    account_id: int
    account_code: str
    account_name: str
    account_type: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class ProfitAndLossRead:
    company_id: int
    start_date: date | None
    end_date: date | None
    total_income: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    income_lines: list[ProfitAndLossLine]
    expense_lines: list[ProfitAndLossLine]


@dataclass(frozen=True, slots=True)
class BalanceSheetLine:
    account_id: int
    account_code: str
    account_name: str
    account_type: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class BalanceSheetRead:
    company_id: int
    as_of_date: date | None
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


@dataclass(frozen=True, slots=True)
class AccountLedgerLine:
    journal_entry_id: int
    entry_no: str
    entry_date: date
    line_no: int
    description: str | None
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


@dataclass(frozen=True, slots=True)
class AccountLedgerRead:
    company_id: int
    account_id: int
    account_code: str
    account_name: str
    account_type: str
    start_date: date | None
    end_date: date | None
    opening_balance: Decimal
    closing_balance: Decimal
    lines: list[AccountLedgerLine]


@dataclass(frozen=True, slots=True)
class GeneralLedgerRead:
    company_id: int
    start_date: date | None
    end_date: date | None
    accounts: list[AccountLedgerRead]