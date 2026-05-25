from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.company_user import (
    CompanyUserCreate,
    CompanyUserRead,
    CompanyUserUpdate,
)
from app.modules.accounting.services.company_user_service import (
    create_company_user,
    get_company,
    get_company_user,
    get_company_user_by_company_and_user,
    get_user,
    list_company_users,
    update_company_user,
)


router = APIRouter(
    prefix="/company-users",
    tags=["Company Users"],
)


@router.post(
    "",
    response_model=CompanyUserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_company_user_endpoint(
    payload: CompanyUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
        allowed_roles={"admin"},
    )

    company = get_company(db=db, company_id=payload.company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    user = get_user(db=db, user_id=payload.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    existing_company_user = get_company_user_by_company_and_user(
        db=db,
        company_id=payload.company_id,
        user_id=payload.user_id,
    )

    if existing_company_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already assigned to this company",
        )

    return create_company_user(
        db=db,
        payload=payload,
    )


@router.get(
    "",
    response_model=list[CompanyUserRead],
)
def list_company_users_endpoint(
    company_id: int = Query(..., ge=1),
    user_id: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
        allowed_roles={"admin", "auditor"},
    )

    return list_company_users(
        db=db,
        company_id=company_id,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{company_user_id}",
    response_model=CompanyUserRead,
)
def get_company_user_endpoint(
    company_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_user = get_company_user(
        db=db,
        company_user_id=company_user_id,
    )

    if not company_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company user not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_user.company_id,
        allowed_roles={"admin", "auditor"},
    )

    return company_user


@router.patch(
    "/{company_user_id}",
    response_model=CompanyUserRead,
)
def update_company_user_endpoint(
    company_user_id: int,
    payload: CompanyUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_user = get_company_user(
        db=db,
        company_user_id=company_user_id,
    )

    if not company_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company user not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_user.company_id,
        allowed_roles={"admin"},
    )

    return update_company_user(
        db=db,
        company_user=company_user,
        payload=payload,
    )