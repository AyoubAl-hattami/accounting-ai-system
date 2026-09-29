from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.application.refunds.dto import (
    CreateRefundCommand,
    PostRefundCommand,
    RefundQuery,
    VoidRefundCommand,
)
from app.application.refunds.use_cases import (
    CreateRefund,
    GetRefund,
    ListRefunds,
    PostRefund,
    VoidRefund,
)
from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.infrastructure.database.sqlalchemy.repositories.refund_repository import (
    SqlAlchemyRefundRepository,
)
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.refund import (
    RefundCreate,
    RefundListRead,
    RefundPostRequest,
    RefundRead,
)
from app.modules.accounting.services.accounting_lookup_facade import (
    find_fiscal_period_for_date,
    find_fiscal_year_for_date,
    get_company_or_none,
)
from app.modules.accounting.services.audit_service import prepare_audit_log

router = APIRouter(
    prefix="/refunds",
    tags=["Refunds"],
)


@router.post(
    "",
    response_model=RefundRead,
    status_code=status.HTTP_201_CREATED,
)
def create_refund_endpoint(
    payload: RefundCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
        allowed_roles={"admin", "accountant"},
    )

    company = get_company_or_none(db=db, company_id=payload.company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    command = CreateRefundCommand(
        company_id=payload.company_id,
        partner_id=payload.partner_id,
        refund_type=payload.refund_type,
        currency_code=payload.currency_code.upper(),
        amount=payload.amount,
        refund_date=payload.refund_date,
        bank_or_cash_account_id=payload.bank_or_cash_account_id,
        receivable_or_payable_account_id=payload.receivable_or_payable_account_id,
        credit_note_id=payload.credit_note_id,
        reference=payload.reference,
        memo=payload.memo,
        created_by_user_id=current_user.id,
    )

    repository = SqlAlchemyRefundRepository(db)
    try:
        refund = CreateRefund(repository).execute(command)
        prepare_audit_log(
            db=db,
            actor=current_user,
            action="create_refund",
            entity="refunds",
            entity_id=refund.id,
            details=f"Created {refund.refund_type} #{refund.id} for {refund.amount} {refund.currency_code}",
        )
        return refund
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=RefundListRead,
)
def list_refunds_endpoint(
    company_id: int = Query(...),
    refund_type: str | None = Query(None),
    partner_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    currency: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
        allowed_roles={"admin", "accountant", "viewer", "auditor"},
    )

    repository = SqlAlchemyRefundRepository(db)
    query = RefundQuery(
        company_id=company_id,
        refund_type=refund_type,
        partner_id=partner_id,
        status=status_filter,
        currency=currency.upper() if currency else None,
        start_date=start_date,
        end_date=end_date,
        search=search,
        skip=skip,
        limit=limit,
    )
    return ListRefunds(repository).execute(query)


@router.get(
    "/{refund_id}",
    response_model=RefundRead,
)
def get_refund_endpoint(
    refund_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyRefundRepository(db)
    refund = GetRefund(repository).execute(refund_id)
    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Refund {refund_id} not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=refund.company_id,
        allowed_roles={"admin", "accountant", "viewer", "auditor"},
    )
    return refund


@router.post(
    "/{refund_id}/post",
    response_model=RefundRead,
)
def post_refund_endpoint(
    refund_id: int,
    payload: RefundPostRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyRefundRepository(db)
    refund = GetRefund(repository).execute(refund_id)
    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Refund {refund_id} not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=refund.company_id,
        allowed_roles={"admin", "accountant"},
    )

    fiscal_year_id = payload.fiscal_year_id if payload else None
    fiscal_period_id = payload.fiscal_period_id if payload else None

    if not fiscal_year_id:
        fy = find_fiscal_year_for_date(db, refund.company_id, refund.refund_date)
        if not fy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No open fiscal year found for refund date {refund.refund_date}.",
            )
        fiscal_year_id = fy.id

    if not fiscal_period_id:
        fp = find_fiscal_period_for_date(db, fiscal_year_id, refund.refund_date)
        if not fp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No open fiscal period found for refund date {refund.refund_date}.",
            )
        fiscal_period_id = fp.id

    command = PostRefundCommand(
        refund_id=refund_id,
        fiscal_year_id=fiscal_year_id,
        fiscal_period_id=fiscal_period_id,
        posted_by_user_id=current_user.id,
    )

    try:
        posted = PostRefund(repository).execute(command)
        prepare_audit_log(
            db=db,
            actor=current_user,
            action="post_refund",
            entity="refunds",
            entity_id=posted.id,
            details=f"Posted {posted.refund_type} #{posted.id} to ledger",
        )
        return posted
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/{refund_id}/void",
    response_model=RefundRead,
)
def void_refund_endpoint(
    refund_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyRefundRepository(db)
    refund = GetRefund(repository).execute(refund_id)
    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Refund {refund_id} not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=refund.company_id,
        allowed_roles={"admin", "accountant"},
    )

    command = VoidRefundCommand(
        refund_id=refund_id,
        voided_by_user_id=current_user.id,
    )

    try:
        voided = VoidRefund(repository).execute(command)
        prepare_audit_log(
            db=db,
            actor=current_user,
            action="void_refund",
            entity="refunds",
            entity_id=voided.id,
            details=f"Voided {voided.refund_type} #{voided.id}",
        )
        return voided
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
