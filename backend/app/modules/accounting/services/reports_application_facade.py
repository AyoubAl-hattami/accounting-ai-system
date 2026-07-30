"""Narrow service-boundary facade for report application use cases."""

from datetime import date

from sqlalchemy.orm import Session

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
from app.application.reports.policies import REPORTABLE_ENTRY_STATUSES
from app.application.reports.use_cases import (
    GetAccountLedger,
    GetBalanceSheet,
    GetGeneralLedger,
    GetProfitAndLoss,
    GetTrialBalance,
)
from app.infrastructure.database.sqlalchemy.repositories.report_repository import (
    SqlAlchemyReportRepository,
)


def get_trial_balance(
    db: Session,
    company_id: int,
    as_of_date: date | None = None,
) -> TrialBalanceRead:
    repository = SqlAlchemyReportRepository(db)
    return GetTrialBalance(repository).execute(
        TrialBalanceQuery(company_id=company_id, as_of_date=as_of_date)
    )


def get_profit_and_loss(
    db: Session,
    company_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> ProfitAndLossRead:
    repository = SqlAlchemyReportRepository(db)
    return GetProfitAndLoss(repository).execute(
        ProfitAndLossQuery(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
        )
    )


def get_balance_sheet(
    db: Session,
    company_id: int,
    as_of_date: date | None = None,
) -> BalanceSheetRead:
    repository = SqlAlchemyReportRepository(db)
    return GetBalanceSheet(repository).execute(
        BalanceSheetQuery(company_id=company_id, as_of_date=as_of_date)
    )


def get_account_ledger(
    db: Session,
    company_id: int,
    account_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> AccountLedgerRead | None:
    repository = SqlAlchemyReportRepository(db)
    return GetAccountLedger(repository).execute(
        AccountLedgerQuery(
            company_id=company_id,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
        )
    )


def get_general_ledger(
    db: Session,
    company_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> GeneralLedgerRead:
    repository = SqlAlchemyReportRepository(db)
    return GetGeneralLedger(repository).execute(
        GeneralLedgerQuery(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
        )
    )
