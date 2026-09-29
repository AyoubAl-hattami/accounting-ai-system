"""Read-only port for accounting reports."""

from __future__ import annotations

from typing import Protocol

from app.application.reports.aging_dto import AgingQuery, AgingReportRead
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
from app.application.reports.statement_dto import (
    PartnerStatementQuery,
    PartnerStatementRead,
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

    def get_aging_report(self, query: AgingQuery) -> AgingReportRead:
        ...

    def get_partner_statement(
        self, query: PartnerStatementQuery
    ) -> PartnerStatementRead:
        ...