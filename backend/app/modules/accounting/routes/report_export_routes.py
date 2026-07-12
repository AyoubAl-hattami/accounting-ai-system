"""
CSV export endpoints for accounting reports.

Each endpoint reuses the same auth, permission, and query filter logic
as the JSON report endpoints, then formats the result as a CSV file
download using report_csv_service.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.modules.accounting.models.user import User
from app.modules.accounting.services.report_service import (
    MissingFiscalYearForReportError,
    get_trial_balance,
    get_profit_and_loss,
    get_balance_sheet,
    get_account_ledger,
    get_general_ledger,
)
from app.modules.accounting.services.report_csv_service import (
    trial_balance_to_csv,
    profit_and_loss_to_csv,
    balance_sheet_to_csv,
    account_ledger_to_csv,
    general_ledger_to_csv,
)


router = APIRouter(
    prefix="/reports",
    tags=["Report Exports"],
)


def _csv_response(csv_text: str, filename: str) -> Response:
    """Create a CSV file download response."""
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/trial-balance/export.csv")
def export_trial_balance_csv(
    company_id: int = Query(..., ge=1),
    as_of_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )

    report = get_trial_balance(
        db=db,
        company_id=company_id,
        as_of_date=as_of_date,
    )

    csv_text = trial_balance_to_csv(report)
    return _csv_response(csv_text, "trial-balance.csv")


@router.get("/profit-loss/export.csv")
def export_profit_loss_csv(
    company_id: int = Query(..., ge=1),
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

    report = get_profit_and_loss(
        db=db,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
    )

    csv_text = profit_and_loss_to_csv(report)
    return _csv_response(csv_text, "profit-and-loss.csv")


@router.get("/balance-sheet/export.csv")
def export_balance_sheet_csv(
    company_id: int = Query(..., ge=1),
    as_of_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )

    try:
        report = get_balance_sheet(
            db=db,
            company_id=company_id,
            as_of_date=as_of_date,
        )
    except MissingFiscalYearForReportError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    csv_text = balance_sheet_to_csv(report)
    return _csv_response(csv_text, "balance-sheet.csv")


@router.get("/account-ledger/export.csv")
def export_account_ledger_csv(
    company_id: int = Query(..., ge=1),
    account_id: int = Query(..., ge=1),
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

    csv_text = account_ledger_to_csv(result)
    return _csv_response(csv_text, "account-ledger.csv")


@router.get("/general-ledger/export.csv")
def export_general_ledger_csv(
    company_id: int = Query(..., ge=1),
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

    report = get_general_ledger(
        db=db,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
    )

    csv_text = general_ledger_to_csv(report)
    return _csv_response(csv_text, "general-ledger.csv")
