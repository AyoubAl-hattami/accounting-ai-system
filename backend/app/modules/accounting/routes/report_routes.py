from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.application.reports.aging_dto import AgingQuery
from app.application.reports.dto import (
    AccountLedgerQuery,
    BalanceSheetQuery,
    GeneralLedgerQuery,
    ProfitAndLossQuery,
    TrialBalanceQuery,
)
from app.application.reports.errors import MissingFiscalYearForReportError
from app.application.reports.use_cases import (
    GetAccountLedger,
    GetAgingReport,
    GetBalanceSheet,
    GetGeneralLedger,
    GetProfitAndLoss,
    GetTrialBalance,
)
from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.infrastructure.database.sqlalchemy.repositories.report_repository import (
    SqlAlchemyReportRepository,
)
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.report import (
    AccountLedgerRead,
    AgingReportRead,
    BalanceSheetRead,
    GeneralLedgerRead,
    ProfitAndLossRead,
    TrialBalanceRead,
)

# Ledger page sizes. A ledger is the report an accountant scrolls, so the
# default is generous; the ceiling exists so a caller cannot ask for an
# unbounded response by naming a huge number.
DEFAULT_LEDGER_LINE_PAGE = 200
MAX_LEDGER_LINE_PAGE = 1000
DEFAULT_LEDGER_ACCOUNT_PAGE = 50
MAX_LEDGER_ACCOUNT_PAGE = 500


router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


@router.get("/currencies")
def report_currencies_endpoint(
    company_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Which currencies this company's reports can be run in.

    Every report totals one currency at a time, so a company that keeps riyal
    and dollar accounts has two trial balances, not one. This is what a report
    page offers as its currency choice.
    """
    ensure_company_access(db=db, current_user=current_user, company_id=company_id)
    base, currencies = SqlAlchemyReportRepository(db).currencies_in_use(company_id)
    return {"base_currency": base, "currencies": currencies}


@router.get(
    "/trial-balance",
    response_model=TrialBalanceRead,
)
def trial_balance_endpoint(
    company_id: int = Query(..., ge=1),
    currency: str | None = Query(default=None, min_length=3, max_length=3),  # the company's own when omitted
    as_of_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )

    repository = SqlAlchemyReportRepository(db)
    return GetTrialBalance(repository).execute(
        TrialBalanceQuery(company_id=company_id, as_of_date=as_of_date, currency=currency)
    )


@router.get(
    "/profit-and-loss",
    response_model=ProfitAndLossRead,
)
def profit_and_loss_endpoint(
    company_id: int = Query(..., ge=1),
    currency: str | None = Query(default=None, min_length=3, max_length=3),  # the company's own when omitted
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )

    repository = SqlAlchemyReportRepository(db)
    return GetProfitAndLoss(repository).execute(
        ProfitAndLossQuery(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            currency=currency,
        )
    )


@router.get(
    "/balance-sheet",
    response_model=BalanceSheetRead,
)
def balance_sheet_endpoint(
    company_id: int = Query(..., ge=1),
    currency: str | None = Query(default=None, min_length=3, max_length=3),  # the company's own when omitted
    as_of_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )

    repository = SqlAlchemyReportRepository(db)
    try:
        return GetBalanceSheet(repository).execute(
            BalanceSheetQuery(company_id=company_id, as_of_date=as_of_date, currency=currency)
        )
    except MissingFiscalYearForReportError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/account-ledger",
    response_model=AccountLedgerRead,
)
def account_ledger_endpoint(
    company_id: int = Query(..., ge=1),
    account_id: int = Query(..., ge=1),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    # Paged by default. The response carries total_lines so a client can tell
    # it has a page rather than the ledger; opening_balance and
    # closing_balance always describe the whole window.
    line_skip: int = Query(default=0, ge=0),
    line_limit: int = Query(default=DEFAULT_LEDGER_LINE_PAGE, ge=1, le=MAX_LEDGER_LINE_PAGE),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )

    repository = SqlAlchemyReportRepository(db)
    result = GetAccountLedger(repository).execute(
        AccountLedgerQuery(
            company_id=company_id,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            line_skip=line_skip,
            line_limit=line_limit,
        )
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return result


@router.get(
    "/general-ledger",
    response_model=GeneralLedgerRead,
)
def general_ledger_endpoint(
    company_id: int = Query(..., ge=1),
    currency: str | None = Query(default=None, min_length=3, max_length=3),  # the company's own when omitted
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    # Paged by ACCOUNT, never by line: a page that split an account would show
    # a running balance with no beginning.
    account_skip: int = Query(default=0, ge=0),
    account_limit: int = Query(
        default=DEFAULT_LEDGER_ACCOUNT_PAGE, ge=1, le=MAX_LEDGER_ACCOUNT_PAGE
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )

    repository = SqlAlchemyReportRepository(db)
    return GetGeneralLedger(repository).execute(
        GeneralLedgerQuery(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            account_skip=account_skip,
            account_limit=account_limit,
            currency=currency,
        )
    )


@router.get(
    "/ar-aging",
    response_model=AgingReportRead,
)
def ar_aging_endpoint(
    company_id: int = Query(..., ge=1),
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    as_of_date: date | None = Query(default=None),
    partner_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )

    effective_as_of = as_of_date or date.today()
    repository = SqlAlchemyReportRepository(db)
    return GetAgingReport(repository).execute(
        AgingQuery(
            company_id=company_id,
            report_type="ar",
            as_of_date=effective_as_of,
            currency=currency or "",
            partner_id=partner_id,
        )
    )


@router.get(
    "/ap-aging",
    response_model=AgingReportRead,
)
def ap_aging_endpoint(
    company_id: int = Query(..., ge=1),
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    as_of_date: date | None = Query(default=None),
    partner_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )

    effective_as_of = as_of_date or date.today()
    repository = SqlAlchemyReportRepository(db)
    return GetAgingReport(repository).execute(
        AgingQuery(
            company_id=company_id,
            report_type="ap",
            as_of_date=effective_as_of,
            currency=currency or "",
            partner_id=partner_id,
        )
    )
