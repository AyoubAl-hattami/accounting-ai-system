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
    count_journal_entries_for_fiscal_year,
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
    find_overlapping_fiscal_period,
    find_overlapping_fiscal_year,
)
from app.modules.accounting.services.audit_service import (
    create_atomic_audit_log,
    prepare_audit_log,
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
    overlapping_year = find_overlapping_fiscal_year(
        db=db,
        company_id=payload.company_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )

    if overlapping_year:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fiscal year dates overlap with an existing fiscal year",
        )
    fiscal_year = create_fiscal_year(db=db, payload=payload)

    create_atomic_audit_log(
        db=db,
        company_id=fiscal_year.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="create_fiscal_year",
        entity_type="fiscal_year",
        entity_id=fiscal_year.id,
        description=f"Created fiscal year {fiscal_year.name}",
    )

    return fiscal_year


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

    date_change_requested = (
        payload.start_date is not None
        or payload.end_date is not None
    )

    if date_change_requested:
        journal_entry_count = count_journal_entries_for_fiscal_year(
            db=db,
            fiscal_year_id=fiscal_year.id,
        )

        if journal_entry_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Fiscal year dates cannot be changed because journal "
                    "entries already exist for this fiscal year"
                ),
            )

    new_start_date = payload.start_date or fiscal_year.start_date
    new_end_date = payload.end_date or fiscal_year.end_date

    if new_end_date < new_start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be greater than or equal to start_date",
        )

    overlapping_year = find_overlapping_fiscal_year(
        db=db,
        company_id=fiscal_year.company_id,
        start_date=new_start_date,
        end_date=new_end_date,
        exclude_fiscal_year_id=fiscal_year.id,
    )

    if overlapping_year:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fiscal year dates overlap with an existing fiscal year",
        )
    old_fiscal_year_values = {
        "name": fiscal_year.name,
        "status": fiscal_year.status,
        "start_date": str(fiscal_year.start_date),
        "end_date": str(fiscal_year.end_date),
    }

    updated = update_fiscal_year(
        db=db,
        fiscal_year=fiscal_year,
        payload=payload,
    )

    create_atomic_audit_log(
        db=db,
        company_id=updated.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="update_fiscal_year",
        entity_type="fiscal_year",
        entity_id=updated.id,
        description=f"Updated fiscal year {updated.name}",
        old_values=old_fiscal_year_values,
        new_values={
            "name": updated.name,
            "status": updated.status,
            "start_date": str(updated.start_date),
            "end_date": str(updated.end_date),
        },
    )

    return updated


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

    overlapping_period = find_overlapping_fiscal_period(
        db=db,
        company_id=payload.company_id,
        fiscal_year_id=payload.fiscal_year_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )

    if overlapping_period:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fiscal period dates overlap with an existing fiscal period",
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

    fiscal_period = create_fiscal_period(db=db, payload=payload)

    create_atomic_audit_log(
        db=db,
        company_id=fiscal_period.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="create_fiscal_period",
        entity_type="fiscal_period",
        entity_id=fiscal_period.id,
        description=f"Created fiscal period {fiscal_period.name}",
    )

    return fiscal_period


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

    if new_end_date < new_start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be greater than or equal to start_date",
        )

    if new_start_date < fiscal_year.start_date or new_end_date > fiscal_year.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal period dates must be within fiscal year dates",
        )

    overlapping_period = find_overlapping_fiscal_period(
        db=db,
        company_id=fiscal_period.company_id,
        fiscal_year_id=fiscal_period.fiscal_year_id,
        start_date=new_start_date,
        end_date=new_end_date,
        exclude_fiscal_period_id=fiscal_period.id,
    )

    if overlapping_period:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fiscal period dates overlap with an existing fiscal period",
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

    old_period_values = {
        "name": fiscal_period.name,
        "status": fiscal_period.status,
        "start_date": str(fiscal_period.start_date),
        "end_date": str(fiscal_period.end_date),
    }

    updated = update_fiscal_period(
        db=db,
        fiscal_period=fiscal_period,
        payload=payload,
    )

    create_atomic_audit_log(
        db=db,
        company_id=updated.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="update_fiscal_period",
        entity_type="fiscal_period",
        entity_id=updated.id,
        description=f"Updated fiscal period {updated.name}",
        old_values=old_period_values,
        new_values={
            "name": updated.name,
            "status": updated.status,
            "start_date": str(updated.start_date),
            "end_date": str(updated.end_date),
        },
    )

    return updated


# -------------------------
# Quick Setup — Fiscal Period for Today
# -------------------------

@router.post(
    "/fiscal/quick-setup-today",
    status_code=status.HTTP_200_OK,
)
def quick_setup_fiscal_period_for_today(
    company_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Idempotently create a fiscal year + fiscal period covering today.
    Existing closed/locked years or periods are not reopened automatically.
    Returns what was created vs. what already existed.
    """
    from datetime import date as _date, timedelta
    from app.core.clock import get_today_date

    company = get_company_or_none(db=db, company_id=company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
        allowed_roles={"admin"},
    )

    today = get_today_date()
    year_start = _date(today.year, 1, 1)
    year_end = _date(today.year, 12, 31)
    month_start = _date(today.year, today.month, 1)
    if today.month == 12:
        month_end = _date(today.year, 12, 31)
    else:
        month_end = _date(today.year, today.month + 1, 1) - timedelta(days=1)

    result = {
        "today": today.isoformat(),
        "fiscal_year_created": False,
        "fiscal_year_opened": False,
        "fiscal_period_created": False,
        "fiscal_period_opened": False,
        "fiscal_year": None,
        "fiscal_period": None,
    }

    # ── Find or create fiscal year ──────────────────────────────────
    fiscal_years = list_fiscal_years(db=db, company_id=company_id, skip=0, limit=500)
    fiscal_year = None
    for fy in fiscal_years:
        if fy.start_date <= today <= fy.end_date:
            fiscal_year = fy
            break

    if fiscal_year is None:
        # Check for overlap first
        overlapping = find_overlapping_fiscal_year(
            db=db, company_id=company_id,
            start_date=year_start, end_date=year_end,
        )
        if overlapping:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An existing fiscal year overlaps today's calendar year but "
                    "does not cover today's date. Review fiscal year setup manually."
                ),
            )
        else:
            fy_payload = FiscalYearCreate(
                company_id=company_id,
                name=f"FY {today.year}",
                start_date=year_start,
                end_date=year_end,
                status="open",
            )
            # Check name collision
            existing_name = get_fiscal_year_by_name(db=db, company_id=company_id, name=fy_payload.name)
            if existing_name:
                fiscal_year = existing_name
            else:
                fiscal_year = create_fiscal_year(db=db, payload=fy_payload)
                result["fiscal_year_created"] = True

                prepare_audit_log(
                    db=db,
                    company_id=company_id,
                    actor=current_user.email,
                    actor_user_id=current_user.id,
                    actor_email=current_user.email,
                    actor_name=current_user.full_name,
                    action="create_fiscal_year",
                    entity_type="fiscal_year",
                    entity_id=fiscal_year.id,
                    description=f"Quick setup: Created fiscal year {fiscal_year.name}",
                )

    if fiscal_year.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Today's fiscal year is closed or locked. "
                "An admin must review and reopen it manually if appropriate."
            ),
        )

    result["fiscal_year"] = {
        "id": fiscal_year.id,
        "name": fiscal_year.name,
        "start_date": fiscal_year.start_date.isoformat(),
        "end_date": fiscal_year.end_date.isoformat(),
        "status": fiscal_year.status,
    }

    # ── Find or create fiscal period ────────────────────────────────
    periods = list_fiscal_periods(
        db=db, company_id=company_id,
        fiscal_year_id=fiscal_year.id, skip=0, limit=500,
    )
    fiscal_period = None
    for fp in periods:
        if fp.start_date <= today <= fp.end_date:
            fiscal_period = fp
            break

    if fiscal_period is None:
        period_name = today.strftime("%B %Y")
        # Check name collision
        existing_name = get_fiscal_period_by_name(
            db=db, fiscal_year_id=fiscal_year.id, name=period_name,
        )
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A fiscal period with today's month name already exists but "
                    "does not cover today's date. Review fiscal period setup manually."
                ),
            )
        else:
            # Determine period_no — use month number, but avoid collisions
            desired_no = today.month
            existing_no = get_fiscal_period_by_no(
                db=db, fiscal_year_id=fiscal_year.id, period_no=desired_no,
            )
            if existing_no:
                # Period number taken but doesn't cover today — use next available
                used_nos = {fp.period_no for fp in periods}
                for n in range(1, 13):
                    if n not in used_nos:
                        desired_no = n
                        break

            fp_payload = FiscalPeriodCreate(
                company_id=company_id,
                fiscal_year_id=fiscal_year.id,
                period_no=desired_no,
                name=period_name,
                start_date=month_start,
                end_date=month_end,
                status="open",
            )
            overlapping_period = find_overlapping_fiscal_period(
                db=db,
                company_id=company_id,
                fiscal_year_id=fiscal_year.id,
                start_date=month_start,
                end_date=month_end,
            )

            if overlapping_period:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Fiscal period dates overlap with an existing fiscal period",
                )

            fiscal_period = create_fiscal_period(db=db, payload=fp_payload)
            result["fiscal_period_created"] = True

            prepare_audit_log(
                db=db,
                company_id=company_id,
                actor=current_user.email,
                actor_user_id=current_user.id,
                actor_email=current_user.email,
                actor_name=current_user.full_name,
                action="create_fiscal_period",
                entity_type="fiscal_period",
                entity_id=fiscal_period.id,
                description=f"Quick setup: Created fiscal period {fiscal_period.name}",
            )

    if fiscal_period.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Today's fiscal period is closed or locked. "
                "An admin must review and reopen it manually if appropriate."
            ),
        )

    result["fiscal_period"] = {
        "id": fiscal_period.id,
        "name": fiscal_period.name,
        "start_date": fiscal_period.start_date.isoformat(),
        "end_date": fiscal_period.end_date.isoformat(),
        "status": fiscal_period.status,
        "period_no": fiscal_period.period_no,
    }

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return result
