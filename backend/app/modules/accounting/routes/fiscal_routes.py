from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.core.pagination import PaginatedResponse
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.fiscal import (
    FiscalPeriodCreate,
    FiscalPeriodRead,
    FiscalPeriodUpdate,
    FiscalYearCreate,
    FiscalYearRead,
    FiscalYearUpdate,
)
from app.modules.accounting.services.fiscal_service import (
    count_fiscal_periods,
    count_fiscal_years,
    create_fiscal_period,
    create_fiscal_year,
    get_company_or_none,
    get_fiscal_period,
    get_fiscal_period_by_name,
    get_fiscal_period_by_no,
    get_fiscal_year,
    get_fiscal_year_by_name,
    list_fiscal_periods,
    list_fiscal_years,
    update_fiscal_period,
    update_fiscal_year,
)


router = APIRouter(tags=["Fiscal"])


# -------------------------
# Fiscal Years
# -------------------------

@router.post(
    "/fiscal-years",
    response_model=FiscalYearRead,
    status_code=status.HTTP_201_CREATED,
)
def create_fiscal_year_endpoint(
    payload: FiscalYearCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_company_or_none(db=db, company_id=payload.company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
        allowed_roles={"admin"},
    )

    existing_year = get_fiscal_year_by_name(
        db=db,
        company_id=payload.company_id,
        name=payload.name,
    )

    if existing_year:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fiscal year name already exists for this company",
        )

    return create_fiscal_year(db=db, payload=payload)


@router.get(
    "/fiscal-years",
    response_model=PaginatedResponse[FiscalYearRead],
)
def list_fiscal_years_endpoint(
    company_id: int = Query(..., ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )

    fiscal_years = list_fiscal_years(
        db=db,
        company_id=company_id,
        skip=skip,
        limit=limit,
    )

    total = count_fiscal_years(
        db=db,
        company_id=company_id,
    )

    return PaginatedResponse[FiscalYearRead](
        items=fiscal_years,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/fiscal-years/{fiscal_year_id}",
    response_model=FiscalYearRead,
)
def get_fiscal_year_endpoint(
    fiscal_year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fiscal_year = get_fiscal_year(db=db, fiscal_year_id=fiscal_year_id)

    if not fiscal_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fiscal year not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=fiscal_year.company_id,
    )

    return fiscal_year


@router.patch(
    "/fiscal-years/{fiscal_year_id}",
    response_model=FiscalYearRead,
)
def update_fiscal_year_endpoint(
    fiscal_year_id: int,
    payload: FiscalYearUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fiscal_year = get_fiscal_year(db=db, fiscal_year_id=fiscal_year_id)

    if not fiscal_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fiscal year not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=fiscal_year.company_id,
        allowed_roles={"admin"},
    )

    if payload.name is not None:
        existing_year = get_fiscal_year_by_name(
            db=db,
            company_id=fiscal_year.company_id,
            name=payload.name,
        )

        if existing_year and existing_year.id != fiscal_year.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Fiscal year name already exists for this company",
            )

    return update_fiscal_year(
        db=db,
        fiscal_year=fiscal_year,
        payload=payload,
    )


# -------------------------
# Fiscal Periods
# -------------------------

@router.post(
    "/fiscal-periods",
    response_model=FiscalPeriodRead,
    status_code=status.HTTP_201_CREATED,
)
def create_fiscal_period_endpoint(
    payload: FiscalPeriodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_company_or_none(db=db, company_id=payload.company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
        allowed_roles={"admin"},
    )

    fiscal_year = get_fiscal_year(db=db, fiscal_year_id=payload.fiscal_year_id)

    if not fiscal_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fiscal year not found",
        )

    if fiscal_year.company_id != payload.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal year must belong to the same company",
        )

    if payload.start_date < fiscal_year.start_date or payload.end_date > fiscal_year.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal period dates must be within fiscal year dates",
        )

    existing_period_no = get_fiscal_period_by_no(
        db=db,
        fiscal_year_id=payload.fiscal_year_id,
        period_no=payload.period_no,
    )

    if existing_period_no:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fiscal period number already exists for this fiscal year",
        )

    existing_period_name = get_fiscal_period_by_name(
        db=db,
        fiscal_year_id=payload.fiscal_year_id,
        name=payload.name,
    )

    if existing_period_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fiscal period name already exists for this fiscal year",
        )

    return create_fiscal_period(db=db, payload=payload)


@router.get(
    "/fiscal-periods",
    response_model=PaginatedResponse[FiscalPeriodRead],
)
def list_fiscal_periods_endpoint(
    company_id: int = Query(..., ge=1),
    fiscal_year_id: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )

    fiscal_periods = list_fiscal_periods(
        db=db,
        company_id=company_id,
        fiscal_year_id=fiscal_year_id,
        skip=skip,
        limit=limit,
    )

    total = count_fiscal_periods(
        db=db,
        company_id=company_id,
        fiscal_year_id=fiscal_year_id,
    )

    return PaginatedResponse[FiscalPeriodRead](
        items=fiscal_periods,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/fiscal-periods/{fiscal_period_id}",
    response_model=FiscalPeriodRead,
)
def get_fiscal_period_endpoint(
    fiscal_period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fiscal_period = get_fiscal_period(
        db=db,
        fiscal_period_id=fiscal_period_id,
    )

    if not fiscal_period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fiscal period not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=fiscal_period.company_id,
    )

    return fiscal_period


@router.patch(
    "/fiscal-periods/{fiscal_period_id}",
    response_model=FiscalPeriodRead,
)
def update_fiscal_period_endpoint(
    fiscal_period_id: int,
    payload: FiscalPeriodUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fiscal_period = get_fiscal_period(
        db=db,
        fiscal_period_id=fiscal_period_id,
    )

    if not fiscal_period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fiscal period not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=fiscal_period.company_id,
        allowed_roles={"admin"},
    )

    fiscal_year = get_fiscal_year(
        db=db,
        fiscal_year_id=fiscal_period.fiscal_year_id,
    )

    if not fiscal_year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fiscal year not found",
        )

    new_start_date = payload.start_date or fiscal_period.start_date
    new_end_date = payload.end_date or fiscal_period.end_date

    if new_start_date < fiscal_year.start_date or new_end_date > fiscal_year.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal period dates must be within fiscal year dates",
        )

    if payload.period_no is not None:
        existing_period_no = get_fiscal_period_by_no(
            db=db,
            fiscal_year_id=fiscal_period.fiscal_year_id,
            period_no=payload.period_no,
        )

        if existing_period_no and existing_period_no.id != fiscal_period.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Fiscal period number already exists for this fiscal year",
            )

    if payload.name is not None:
        existing_period_name = get_fiscal_period_by_name(
            db=db,
            fiscal_year_id=fiscal_period.fiscal_year_id,
            name=payload.name,
        )

        if existing_period_name and existing_period_name.id != fiscal_period.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Fiscal period name already exists for this fiscal year",
            )

    return update_fiscal_period(
        db=db,
        fiscal_period=fiscal_period,
        payload=payload,
    )