"""Read-only port for accounting reports."""

from typing import Protocol

from app.application.reports.dto import (
    AccountLedgerQuery,
    AccountLedgerRead,
    BalanceSheetQuery,
    BalanceSheetRead,
    GeneralLedgerQuery,
    GeneralLedgerRead,
    ProfitAndLossQuery,
    ProfitAndLossRead,
    TrialBalanceQuery,
    TrialBalanceRead,
)


class ReportRepository(Protocol):
    def get_trial_balance(self, query: TrialBalanceQuery) -> TrialBalanceRead:
        ...

    def get_profit_and_loss(self, query: ProfitAndLossQuery) -> ProfitAndLossRead:
        ...

    def get_balance_sheet(self, query: BalanceSheetQuery) -> BalanceSheetRead:
        ...

    def get_account_ledger(
        self, query: AccountLedgerQuery
    ) -> AccountLedgerRead | None:
        ...

    def get_general_ledger(self, query: GeneralLedgerQuery) -> GeneralLedgerRead:
        ...