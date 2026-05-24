from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.accounting.schemas.company import (
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
)
from app.modules.accounting.services.company_service import (
    create_company,
    get_company,
    list_companies,
    update_company,
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
):
    return create_company(db=db, payload=payload)


@router.get(
    "",
    response_model=list[CompanyRead],
)
def list_companies_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_companies(db=db, skip=skip, limit=limit)


@router.get(
    "/{company_id}",
    response_model=CompanyRead,
)
def get_company_endpoint(
    company_id: int,
    db: Session = Depends(get_db),
):
    company = get_company(db=db, company_id=company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
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
):
    company = get_company(db=db, company_id=company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    return update_company(db=db, company=company, payload=payload)