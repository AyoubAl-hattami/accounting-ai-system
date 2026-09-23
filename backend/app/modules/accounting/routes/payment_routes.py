from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.application.payments.dto import (
    CreatePaymentAllocationCommand,
    CreatePaymentCommand,
    PaymentQuery,
    PostPaymentCommand,
    VoidPaymentCommand,
)
from app.application.payments.use_cases import (
    CreatePayment,
    GetPayment,
    ListPayments,
    PostPayment,
    VoidPayment,
)
from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.infrastructure.database.sqlalchemy.repositories.payment_repository import (
    SqlAlchemyPaymentRepository,
)
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.payment import (
    PaymentCreate,
    PaymentPageResponse,
    PaymentPostRequest,
    PaymentResponse,
)
from app.modules.accounting.services.accounting_lookup_facade import (
    find_fiscal_period_for_date,
    find_fiscal_year_for_date,
    get_company_or_none,
)
from app.modules.accounting.services.audit_service import prepare_audit_log

router = APIRouter(
    prefix="/payments",
    tags=["Payments & Receipts"],
)


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment_endpoint(
    payload: PaymentCreate,
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

    allocations = [
        CreatePaymentAllocationCommand(
            invoice_id=a.invoice_id,
            amount=a.amount,
        )
        for a in payload.allocations
    ]

    command = CreatePaymentCommand(
        company_id=payload.company_id,
        partner_id=payload.partner_id,
        payment_type=payload.payment_type,
        currency_code=payload.currency_code.upper(),
        amount=payload.amount,
        payment_date=payload.payment_date,
        bank_or_cash_account_id=payload.bank_or_cash_account_id,
        receivable_or_payable_account_id=payload.receivable_or_payable_account_id,
        allocations=allocations,
        reference=payload.reference,
        memo=payload.memo,
        created_by_user_id=current_user.id,
    )

    repository = SqlAlchemyPaymentRepository(db)
    try:
        payment = CreatePayment(repository).execute(command)
        action_name = (
            "create_customer_receipt"
            if payment.payment_type == "customer_receipt"
            else "create_vendor_payment"
        )
        prepare_audit_log(
            db=db,
            company_id=payment.company_id,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action=action_name,
            entity_type="payment",
            entity_id=payment.id,
            description=f"Created {payment.payment_type} #{payment.id} for {payment.amount} {payment.currency_code}",
        )
        db.commit()
        return payment
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=PaymentPageResponse,
)
def list_payments_endpoint(
    company_id: int = Query(..., ge=1),
    payment_type: str | None = Query(None),
    partner_id: int | None = Query(None),
    status: str | None = Query(None),
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
        allowed_roles={"admin", "accountant", "auditor", "user"},
    )

    query = PaymentQuery(
        company_id=company_id,
        payment_type=payment_type,
        partner_id=partner_id,
        status=status,
        currency=currency.upper() if currency else None,
        start_date=start_date,
        end_date=end_date,
        search=search,
        skip=skip,
        limit=limit,
    )
    repository = SqlAlchemyPaymentRepository(db)
    return ListPayments(repository).execute(query)


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment_endpoint(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyPaymentRepository(db)
    payment = GetPayment(repository).execute(payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payment.company_id,
        allowed_roles={"admin", "accountant", "auditor", "user"},
    )

    return payment


@router.post(
    "/{payment_id}/post",
    response_model=PaymentResponse,
)
def post_payment_endpoint(
    payment_id: int,
    payload: PaymentPostRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyPaymentRepository(db)
    payment = GetPayment(repository).execute(payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payment.company_id,
        allowed_roles={"admin", "accountant"},
    )

    if payment.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot post payment in status '{payment.status}'. Must be 'draft'.",
        )

    # Resolve fiscal year and period
    fiscal_year_id = payload.fiscal_year_id if payload else None
    fiscal_period_id = payload.fiscal_period_id if payload else None

    if not fiscal_year_id or not fiscal_period_id:
        fiscal_year = find_fiscal_year_for_date(
            db=db, company_id=payment.company_id, entry_date=payment.payment_date
        )
        if not fiscal_year:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No fiscal year covers payment date {payment.payment_date}",
            )
        fiscal_year_id = fiscal_year.id

        fiscal_period = find_fiscal_period_for_date(
            db=db, company_id=payment.company_id, entry_date=payment.payment_date
        )
        if not fiscal_period:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No fiscal period covers payment date {payment.payment_date}",
            )
        if fiscal_period.status != "open":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fiscal period '{fiscal_period.name}' is {fiscal_period.status}. Posting is only allowed in open periods.",
            )
        fiscal_period_id = fiscal_period.id

    command = PostPaymentCommand(
        payment_id=payment_id,
        fiscal_year_id=fiscal_year_id,
        fiscal_period_id=fiscal_period_id,
        posted_by_user_id=current_user.id,
    )

    try:
        posted = PostPayment(repository).execute(command)
        action_name = (
            "post_customer_receipt"
            if posted.payment_type == "customer_receipt"
            else "post_vendor_payment"
        )
        prepare_audit_log(
            db=db,
            company_id=posted.company_id,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action=action_name,
            entity_type="payment",
            entity_id=posted.id,
            description=f"Posted {posted.payment_type} #{posted.id} to General Ledger (Entry ID: {posted.journal_entry_id})",
        )
        db.commit()
        return posted
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/{payment_id}/void",
    response_model=PaymentResponse,
)
def void_payment_endpoint(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyPaymentRepository(db)
    payment = GetPayment(repository).execute(payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payment.company_id,
        allowed_roles={"admin", "accountant"},
    )

    command = VoidPaymentCommand(
        payment_id=payment_id,
        voided_by_user_id=current_user.id,
    )

    try:
        voided = VoidPayment(repository).execute(command)
        prepare_audit_log(
            db=db,
            company_id=voided.company_id,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action="void_payment",
            entity_type="payment",
            entity_id=voided.id,
            description=f"Voided payment #{voided.id}",
        )
        db.commit()
        return voided
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
