"""
PDF export endpoints for accounting reports.

Each endpoint reuses the same auth, permission, and query filter logic
as the JSON and CSV report endpoints, then formats the result as a PDF
file download using report_pdf_service.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

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
from app.modules.accounting.services.report_pdf_service import (
    trial_balance_to_pdf,
    profit_and_loss_to_pdf,
    balance_sheet_to_pdf,
    account_ledger_to_pdf,
    general_ledger_to_pdf,
)


router = APIRouter(
    prefix="/reports",
    tags=["Report Exports"],
)


def _pdf_response(pdf_bytes: bytes, filename: str) -> Response:
    """Create a PDF file download response."""
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/trial-balance/export.pdf")
def export_trial_balance_pdf(
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

    repository = SqlAlchemyReportRepository(db)
    report = GetTrialBalance(repository).execute(
        TrialBalanceQuery(company_id=company_id, as_of_date=as_of_date)
    )

    pdf_bytes = trial_balance_to_pdf(report)
    return _pdf_response(pdf_bytes, "trial-balance.pdf")


@router.get("/profit-loss/export.pdf")
def export_profit_loss_pdf(
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

    repository = SqlAlchemyReportRepository(db)
    report = GetProfitAndLoss(repository).execute(
        ProfitAndLossQuery(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
        )
    )

    pdf_bytes = profit_and_loss_to_pdf(report)
    return _pdf_response(pdf_bytes, "profit-and-loss.pdf")


@router.get("/balance-sheet/export.pdf")
def export_balance_sheet_pdf(
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
        repository = SqlAlchemyReportRepository(db)
        report = GetBalanceSheet(repository).execute(
            BalanceSheetQuery(company_id=company_id, as_of_date=as_of_date)
        )
    except MissingFiscalYearForReportError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    pdf_bytes = balance_sheet_to_pdf(report)
    return _pdf_response(pdf_bytes, "balance-sheet.pdf")


@router.get("/account-ledger/export.pdf")
def export_account_ledger_pdf(
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

    repository = SqlAlchemyReportRepository(db)
    result = GetAccountLedger(repository).execute(
        AccountLedgerQuery(
            company_id=company_id,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
        )
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    pdf_bytes = account_ledger_to_pdf(result)
    return _pdf_response(pdf_bytes, "account-ledger.pdf")


@router.get("/general-ledger/export.pdf")
def export_general_ledger_pdf(
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

    repository = SqlAlchemyReportRepository(db)
    report = GetGeneralLedger(repository).execute(
        GeneralLedgerQuery(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
        )
    )

    pdf_bytes = general_ledger_to_pdf(report)
    return _pdf_response(pdf_bytes, "general-ledger.pdf")
