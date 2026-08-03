from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.core.pagination import PaginatedResponse
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.company import (
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
)
from app.modules.accounting.schemas.company_user import CompanyUserCreate
from app.application.companies.dto import CreateCompanyCommand, UpdateCompanyCommand
from app.application.companies.use_cases import CreateCompany, GetCompany, ListCompanies, UpdateCompany
from app.application.subscriptions.policy import days_remaining, effective_status, grants_access
from app.infrastructure.database.sqlalchemy.repositories.company_repository import SqlAlchemyCompanyRepository
from app.infrastructure.database.sqlalchemy.repositories.subscription_repository import (
    SqlAlchemySubscriptionRepository,
)
from app.modules.accounting.schemas.company_subscription import (
    CompanySubscriptionStatusRead,
)
from app.modules.accounting.services.company_user_service import (
    create_company_user,
)
from app.modules.accounting.services.audit_service import prepare_audit_log


router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


@router.post(
    "",
    response_model=CompanyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_company_endpoint(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = SqlAlchemyCompanyRepository(db)
    company = CreateCompany(repo).execute(
        CreateCompanyCommand(
            name=payload.name,
            base_currency=payload.base_currency,
            legal_name=payload.legal_name,
            registration_no=payload.registration_no,
            tax_no=payload.tax_no,
            address=payload.address,
            is_active=payload.is_active,
        )
    )

    create_company_user(
        db=db,
        payload=CompanyUserCreate(
            company_id=company.id,
            user_id=current_user.id,
            role="admin",
            is_active=True,
        ),
    )

    # A new tenant starts active with no expiry; the platform owner sets the
    # term explicitly rather than the client stumbling into a surprise lockout.
    SqlAlchemySubscriptionRepository(db).get_or_create(company.id)

    prepare_audit_log(
        db=db,
        company_id=company.id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="create_company",
        entity_type="company",
        entity_id=company.id,
        description=f"Created company {company.name}",
    )
    db.commit()

    return company


@router.get(
    "",
    response_model=PaginatedResponse[CompanyRead],
)
def list_companies_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = SqlAlchemyCompanyRepository(db)
    user_id = None if current_user.is_superuser else current_user.id
    page = ListCompanies(repo).execute(user_id=user_id, skip=skip, limit=limit)
    return PaginatedResponse[CompanyRead](
        items=list(page.items),
        total=page.total,
        skip=page.skip,
        limit=page.limit,
    )


@router.get(
    "/{company_id}",
    response_model=CompanyRead,
)
def get_company_endpoint(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = SqlAlchemyCompanyRepository(db)
    company = GetCompany(repo).execute(company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    # Exempt from the subscription gate: reading the company profile carries no
    # accounting data and the shell needs it to explain why access is blocked.
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company.id,
        require_active_subscription=False,
    )

    return company


@router.get(
    "/{company_id}/subscription",
    response_model=CompanySubscriptionStatusRead,
)
def get_company_subscription_status_endpoint(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Let a member see whether its own company may transact.

    Exempt from the subscription gate on purpose: a locked-out client needs this
    to render the inactive screen instead of a wall of failed requests.  It
    exposes no other company's data and no accounting figures.
    """
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
        require_active_subscription=False,
    )

    subscription = SqlAlchemySubscriptionRepository(db).get(company_id)

    if subscription is None:
        return CompanySubscriptionStatusRead(
            company_id=company_id,
            effective_status="active",
            expires_at=None,
            days_remaining=None,
            is_active=True,
        )

    return CompanySubscriptionStatusRead(
        company_id=company_id,
        effective_status=effective_status(subscription.status, subscription.expires_at),
        expires_at=subscription.expires_at,
        days_remaining=days_remaining(subscription.expires_at),
        is_active=grants_access(subscription.status, subscription.expires_at),
    )


@router.patch(
    "/{company_id}",
    response_model=CompanyRead,
)
def update_company_endpoint(
    company_id: int,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = SqlAlchemyCompanyRepository(db)
    company = GetCompany(repo).execute(company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company.id,
        allowed_roles={"admin"},
    )

    update_data = payload.model_dump(exclude_unset=True)
    updated = UpdateCompany(repo).execute(
        UpdateCompanyCommand(
            company_id=company_id,
            fields=frozenset(update_data.keys()),
            **update_data,
        )
    )

    prepare_audit_log(
        db=db,
        company_id=updated.id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="update_company",
        entity_type="company",
        entity_id=updated.id,
        description=f"Updated company {updated.name}",
    )
    db.commit()

    return updated
