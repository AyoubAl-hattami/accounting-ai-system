from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.invoices.dto import (
    CreateInvoiceCommand,
    CreateInvoiceLineCommand,
    InvoiceQuery,
    PostInvoiceCommand,
    UpdateInvoiceCommand,
    VoidInvoiceCommand,
)
from app.application.invoices.use_cases import (
    CreateInvoice,
    GetInvoice,
    ListInvoices,
    PostInvoice,
    UpdateInvoice,
    VoidInvoice,
)
from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.infrastructure.database.sqlalchemy.repositories.invoice_repository import (
    SqlAlchemyInvoiceRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.partner_repository import (
    SqlAlchemyPartnerRepository,
)
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.invoice import (
    InvoiceCreate,
    InvoicePageResponse,
    InvoicePostRequest,
    InvoiceResponse,
    InvoiceUpdate,
)
from app.modules.accounting.services.accounting_lookup_facade import (
    find_fiscal_period_for_date,
    find_fiscal_year_for_date,
    get_company_or_none,
)
from app.modules.accounting.services.audit_service import prepare_audit_log

router = APIRouter(
    prefix="/invoices",
    tags=["Invoices & Bills"],
)


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invoice_endpoint(
    payload: InvoiceCreate,
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

    partner = SqlAlchemyPartnerRepository(db).get_by_id(payload.partner_id)
    if partner is None or partner.company_id != payload.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found for this company",
        )

    if payload.invoice_type == "out_invoice" and not partner.is_customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected partner is not marked as a customer.",
        )

    if payload.invoice_type == "in_invoice" and not partner.is_vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected partner is not marked as a vendor.",
        )

    # Resolve currency: payload currency -> partner currency -> company base currency
    resolved_currency = (
        payload.currency or partner.currency or company.base_currency
    ).upper()

    lines = [
        CreateInvoiceLineCommand(
            description=line.description.strip(),
            quantity=line.quantity,
            unit_price=line.unit_price,
            account_id=line.account_id,
        )
        for line in payload.lines
    ]

    command = CreateInvoiceCommand(
        company_id=payload.company_id,
        partner_id=payload.partner_id,
        invoice_type=payload.invoice_type,
        invoice_no=payload.invoice_no,
        reference=payload.reference,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        currency=resolved_currency,
        tax_amount=payload.tax_amount or Decimal("0.00"),
        notes=payload.notes,
        created_by_user_id=current_user.id,
        lines=lines,
    )

    repository = SqlAlchemyInvoiceRepository(db)
    try:
        invoice = CreateInvoice(repository).execute(command)
        action_name = "create_sales_invoice" if invoice.invoice_type == "out_invoice" else "create_purchase_bill"
        prepare_audit_log(
            db=db,
            company_id=invoice.company_id,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action=action_name,
            entity_type="invoice",
            entity_id=invoice.id,
            description=f"Created {invoice.invoice_type} #{invoice.invoice_no}",
        )
        db.commit()
        return invoice
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invoice number '{payload.invoice_no}' already exists for this document type.",
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=InvoicePageResponse,
)
def list_invoices_endpoint(
    company_id: int = Query(..., ge=1),
    invoice_type: str | None = Query(None),
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

    query = InvoiceQuery(
        company_id=company_id,
        invoice_type=invoice_type,
        partner_id=partner_id,
        status=status,
        currency=currency.upper() if currency else None,
        start_date=start_date,
        end_date=end_date,
        search=search,
        skip=skip,
        limit=limit,
    )
    repository = SqlAlchemyInvoiceRepository(db)
    return ListInvoices(repository).execute(query)


@router.get(
    "/open-items",
    response_model=list[InvoiceResponse],
)
def get_open_invoices_endpoint(
    company_id: int = Query(..., ge=1),
    partner_id: int = Query(..., ge=1),
    currency: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
        allowed_roles={"admin", "accountant", "auditor", "user"},
    )

    repository = SqlAlchemyInvoiceRepository(db)
    return repository.get_open_invoices(
        company_id=company_id,
        partner_id=partner_id,
        currency=currency,
    )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
)
def get_invoice_endpoint(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyInvoiceRepository(db)
    invoice = GetInvoice(repository).execute(invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=invoice.company_id,
        allowed_roles={"admin", "accountant", "auditor", "user"},
    )

    return invoice


@router.patch(
    "/{invoice_id}",
    response_model=InvoiceResponse,
)
def update_invoice_endpoint(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyInvoiceRepository(db)
    existing = GetInvoice(repository).execute(invoice_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=existing.company_id,
        allowed_roles={"admin", "accountant"},
    )

    if existing.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit invoice in status '{existing.status}'. Only draft invoices can be modified.",
        )

    update_fields = set(payload.model_dump(exclude_unset=True).keys())
    lines = None
    if payload.lines is not None:
        lines = [
            CreateInvoiceLineCommand(
                description=line.description.strip(),
                quantity=line.quantity,
                unit_price=line.unit_price,
                account_id=line.account_id,
            )
            for line in payload.lines
        ]

    command = UpdateInvoiceCommand(
        invoice_id=invoice_id,
        partner_id=payload.partner_id,
        reference=payload.reference,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        tax_amount=payload.tax_amount,
        notes=payload.notes,
        lines=lines,
        fields=frozenset(update_fields),
    )

    try:
        updated = UpdateInvoice(repository).execute(command)
        prepare_audit_log(
            db=db,
            company_id=updated.company_id,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action="update_invoice",
            entity_type="invoice",
            entity_id=updated.id,
            description=f"Updated invoice #{updated.invoice_no}",
        )
        db.commit()
        return updated
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/{invoice_id}/post",
    response_model=InvoiceResponse,
)
def post_invoice_endpoint(
    invoice_id: int,
    payload: InvoicePostRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyInvoiceRepository(db)
    invoice = GetInvoice(repository).execute(invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=invoice.company_id,
        allowed_roles={"admin", "accountant"},
    )

    if invoice.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot post invoice in status '{invoice.status}'. Must be 'draft'.",
        )

    # 1. Resolve fiscal year and period
    fiscal_year = find_fiscal_year_for_date(db=db, company_id=invoice.company_id, entry_date=invoice.issue_date)
    if not fiscal_year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No fiscal year covers invoice date {invoice.issue_date}",
        )

    fiscal_period = find_fiscal_period_for_date(db=db, company_id=invoice.company_id, entry_date=invoice.issue_date)
    if not fiscal_period:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No fiscal period covers invoice date {invoice.issue_date}",
        )

    if fiscal_period.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fiscal period '{fiscal_period.name}' is {fiscal_period.status}. Posting is only allowed in open periods.",
        )

    # 2. Resolve target receivable/payable account
    target_account_id = payload.receivable_or_payable_account_id
    if not target_account_id:
        partner = SqlAlchemyPartnerRepository(db).get_by_id(invoice.partner_id)
        if partner:
            if invoice.invoice_type == "out_invoice" and partner.receivable_account_id:
                target_account_id = partner.receivable_account_id
            elif invoice.invoice_type == "in_invoice" and partner.payable_account_id:
                target_account_id = partner.payable_account_id

    # Fallback to standard system account of matching subtype & currency
    if not target_account_id:
        expected_subtype = "receivable" if invoice.invoice_type == "out_invoice" else "payable"
        account = db.scalar(
            select(Account).where(
                Account.company_id == invoice.company_id,
                Account.account_subtype == expected_subtype,
                Account.currency == invoice.currency,
                Account.is_active.is_(True),
            )
        )
        if account:
            target_account_id = account.id

    if not target_account_id:
        target_name = "Accounts Receivable" if invoice.invoice_type == "out_invoice" else "Accounts Payable"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No suitable {target_name} account found in currency '{invoice.currency}'. "
                f"Please select or configure an account with subtype '{expected_subtype}' in {invoice.currency}."
            ),
        )

    command = PostInvoiceCommand(
        invoice_id=invoice_id,
        receivable_or_payable_account_id=target_account_id,
        fiscal_year_id=fiscal_year.id,
        fiscal_period_id=fiscal_period.id,
        posted_by_user_id=current_user.id,
    )

    try:
        posted = PostInvoice(repository).execute(command)
        action_name = "post_sales_invoice" if posted.invoice_type == "out_invoice" else "post_purchase_bill"
        prepare_audit_log(
            db=db,
            company_id=posted.company_id,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action=action_name,
            entity_type="invoice",
            entity_id=posted.id,
            description=f"Posted {posted.invoice_type} #{posted.invoice_no} to General Ledger (Entry ID: {posted.journal_entry_id})",
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
    "/{invoice_id}/void",
    response_model=InvoiceResponse,
)
def void_invoice_endpoint(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyInvoiceRepository(db)
    invoice = GetInvoice(repository).execute(invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=invoice.company_id,
        allowed_roles={"admin", "accountant"},
    )

    command = VoidInvoiceCommand(
        invoice_id=invoice_id,
        voided_by_user_id=current_user.id,
    )

    try:
        voided = VoidInvoice(repository).execute(command)
        prepare_audit_log(
            db=db,
            company_id=voided.company_id,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action="void_invoice",
            entity_type="invoice",
            entity_id=voided.id,
            description=f"Voided invoice #{voided.invoice_no}",
        )
        db.commit()
        return voided
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
