from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.accounting.schemas.report import (
    TrialBalanceRead,
    ProfitAndLossRead,
    BalanceSheetRead,
    AccountLedgerRead,
    GeneralLedgerRead,
)
from app.modules.accounting.services.report_service import (
    get_trial_balance,
    get_profit_and_loss,
    get_balance_sheet,
    get_account_ledger,
    get_general_ledger,
)


router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


@router.get(
    "/trial-balance",
    response_model=TrialBalanceRead,
)
def trial_balance_endpoint(
    company_id: int = Query(..., ge=1),
    as_of_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return get_trial_balance(
        db=db,
        company_id=company_id,
        as_of_date=as_of_date,
    )
@router.get(
    "/profit-and-loss",
    response_model=ProfitAndLossRead,
)
def profit_and_loss_endpoint(
    company_id: int = Query(..., ge=1),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return get_profit_and_loss(
        db=db,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
    )
@router.get(
    "/balance-sheet",
    response_model=BalanceSheetRead,
)
def balance_sheet_endpoint(
    company_id: int = Query(..., ge=1),
    as_of_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return get_balance_sheet(
        db=db,
        company_id=company_id,
        as_of_date=as_of_date,
    )
@router.get(
    "/account-ledger",
    response_model=AccountLedgerRead,
)
def account_ledger_endpoint(
    company_id: int = Query(..., ge=1),
    account_id: int = Query(..., ge=1),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    result = get_account_ledger(
        db=db,
        company_id=company_id,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
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
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return get_general_ledger(
        db=db,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
    )