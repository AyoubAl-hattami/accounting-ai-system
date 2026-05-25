from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.company import (
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
)
from app.modules.accounting.schemas.company_user import CompanyUserCreate
from app.modules.accounting.services.company_service import (
    create_company,
    get_company,
    list_companies,
    update_company,
)
from app.modules.accounting.services.company_user_service import (
    create_company_user,
    list_company_users,
)


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
    company = create_company(db=db, payload=payload)

    create_company_user(
        db=db,
        payload=CompanyUserCreate(
            company_id=company.id,
            user_id=current_user.id,
            role="admin",
            is_active=True,
        ),
    )

    return company


@router.get(
    "",
    response_model=list[CompanyRead],
)
def list_companies_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.is_superuser:
        return list_companies(
            db=db,
            skip=skip,
            limit=limit,
        )

    company_user_links = list_company_users(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    companies = []

    for link in company_user_links:
        if not link.is_active:
            continue

        company = get_company(db=db, company_id=link.company_id)

        if company:
            companies.append(company)

    return companies


@router.get(
    "/{company_id}",
    response_model=CompanyRead,
)
def get_company_endpoint(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_company(db=db, company_id=company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company.id,
    )

    return company


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
    company = get_company(db=db, company_id=company_id)

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

    return update_company(
        db=db,
        company=company,
        payload=payload,
    )