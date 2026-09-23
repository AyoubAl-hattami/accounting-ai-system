"""Accounting report application use cases."""

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
from app.application.reports.ports import ReportRepository
from app.application.reports.statement_dto import (
    PartnerStatementQuery,
    PartnerStatementRead,
)


class GetTrialBalance:
    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    def execute(self, query: TrialBalanceQuery) -> TrialBalanceRead:
        return self._repository.get_trial_balance(query)


class GetProfitAndLoss:
    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    def execute(self, query: ProfitAndLossQuery) -> ProfitAndLossRead:
        return self._repository.get_profit_and_loss(query)


class GetBalanceSheet:
    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    def execute(self, query: BalanceSheetQuery) -> BalanceSheetRead:
        return self._repository.get_balance_sheet(query)


class GetAccountLedger:
    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    def execute(self, query: AccountLedgerQuery) -> AccountLedgerRead | None:
        return self._repository.get_account_ledger(query)


class GetGeneralLedger:
    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    def execute(self, query: GeneralLedgerQuery) -> GeneralLedgerRead:
        return self._repository.get_general_ledger(query)


class GetAgingReport:
    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    def execute(self, query: AgingQuery) -> AgingReportRead:
        return self._repository.get_aging_report(query)


class GetPartnerStatement:
    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    def execute(self, query: PartnerStatementQuery) -> PartnerStatementRead:
        return self._repository.get_partner_statement(query)