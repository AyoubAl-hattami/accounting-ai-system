from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.partners.dto import (
    CreatePartnerCommand,
    PartnerQuery,
    UpdatePartnerCommand,
)
from app.application.partners.use_cases import (
    CreatePartner,
    GetPartner,
    ListPartners,
    UpdatePartner,
)
from app.application.reports.statement_dto import PartnerStatementQuery
from app.application.reports.use_cases import GetPartnerStatement
from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.infrastructure.database.sqlalchemy.repositories.partner_repository import (
    SqlAlchemyPartnerRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.report_repository import (
    SqlAlchemyReportRepository,
)
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.partner import (
    PartnerCreate,
    PartnerPageResponse,
    PartnerResponse,
    PartnerUpdate,
)
from app.modules.accounting.schemas.report import PartnerStatementRead
from app.modules.accounting.services.accounting_lookup_facade import get_company_or_none
from app.modules.accounting.services.audit_service import prepare_audit_log

router = APIRouter(
    prefix="/partners",
    tags=["Partners (Customers & Vendors)"],
)


@router.post(
    "",
    response_model=PartnerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_partner_endpoint(
    payload: PartnerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
        allowed_roles={"admin", "accountant"},
    )

    if not payload.is_customer and not payload.is_vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A partner must be designated as a customer, vendor, or both.",
        )

    company = get_company_or_none(db=db, company_id=payload.company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    currency = payload.currency or company.base_currency.upper()

    command = CreatePartnerCommand(
        company_id=payload.company_id,
        name=payload.name,
        code=payload.code,
        is_customer=payload.is_customer,
        is_vendor=payload.is_vendor,
        currency=currency,
        email=payload.email,
        phone=payload.phone,
        tax_id=payload.tax_id,
        address=payload.address,
        receivable_account_id=payload.receivable_account_id,
        payable_account_id=payload.payable_account_id,
        is_active=payload.is_active,
    )

    repository = SqlAlchemyPartnerRepository(db)
    try:
        partner = CreatePartner(repository).execute(command)
        prepare_audit_log(
            db=db,
            company_id=partner.company_id,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action="create_partner",
            entity_type="partner",
            entity_id=partner.id,
            description=f"Created partner {partner.code} - {partner.name}",
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Partner code '{payload.code}' already exists in this company.",
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return partner


@router.get(
    "",
    response_model=PartnerPageResponse,
)
def list_partners_endpoint(
    company_id: int = Query(..., ge=1),
    is_customer: bool | None = Query(None),
    is_vendor: bool | None = Query(None),
    is_active: bool | None = Query(None),
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

    query = PartnerQuery(
        company_id=company_id,
        is_customer=is_customer,
        is_vendor=is_vendor,
        is_active=is_active,
        search=search,
        skip=skip,
        limit=limit,
    )
    repository = SqlAlchemyPartnerRepository(db)
    return ListPartners(repository).execute(query)


@router.get(
    "/{partner_id}",
    response_model=PartnerResponse,
)
def get_partner_endpoint(
    partner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyPartnerRepository(db)
    partner = GetPartner(repository).execute(partner_id)
    if partner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=partner.company_id,
        allowed_roles={"admin", "accountant", "auditor", "user"},
    )

    return partner


@router.patch(
    "/{partner_id}",
    response_model=PartnerResponse,
)
def update_partner_endpoint(
    partner_id: int,
    payload: PartnerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyPartnerRepository(db)
    existing = GetPartner(repository).execute(partner_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=existing.company_id,
        allowed_roles={"admin", "accountant"},
    )

    update_fields = set(payload.model_dump(exclude_unset=True).keys())
    command = UpdatePartnerCommand(
        partner_id=partner_id,
        name=payload.name,
        code=payload.code,
        is_customer=payload.is_customer,
        is_vendor=payload.is_vendor,
        email=payload.email,
        phone=payload.phone,
        tax_id=payload.tax_id,
        address=payload.address,
        receivable_account_id=payload.receivable_account_id,
        payable_account_id=payload.payable_account_id,
        is_active=payload.is_active,
        fields=frozenset(update_fields),
    )

    try:
        updated = UpdatePartner(repository).execute(command)
        prepare_audit_log(
            db=db,
            company_id=updated.company_id,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action="update_partner",
            entity_type="partner",
            entity_id=updated.id,
            description=f"Updated partner {updated.code} - {updated.name}",
        )
        db.commit()
        return updated
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Partner code already exists in this company.",
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/{id}/statement",
    response_model=PartnerStatementRead,
)
def partner_statement_endpoint(
    id: int,
    company_id: int = Query(..., ge=1),
    date_from: date = Query(...),
    date_to: date = Query(...),
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )

    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from cannot be after date_to",
        )

    repository = SqlAlchemyReportRepository(db)
    try:
        return GetPartnerStatement(repository).execute(
            PartnerStatementQuery(
                company_id=company_id,
                partner_id=id,
                currency=currency or "",
                date_from=date_from,
                date_to=date_to,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
