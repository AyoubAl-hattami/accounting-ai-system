from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.accounting.models.company import Company
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.schemas.fiscal import (
    FiscalPeriodCreate,
    FiscalPeriodUpdate,
    FiscalYearCreate,
    FiscalYearUpdate,
)


def get_company_or_none(db: Session, company_id: int) -> Company | None:
    statement = select(Company).where(Company.id == company_id)
    return db.scalar(statement)


# -------------------------
# Fiscal Years
# -------------------------

def create_fiscal_year(db: Session, payload: FiscalYearCreate) -> FiscalYear:
    fiscal_year = FiscalYear(
        company_id=payload.company_id,
        name=payload.name.strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
    )

    db.add(fiscal_year)
    db.commit()
    db.refresh(fiscal_year)

    return fiscal_year


def get_fiscal_year(db: Session, fiscal_year_id: int) -> FiscalYear | None:
    statement = select(FiscalYear).where(FiscalYear.id == fiscal_year_id)
    return db.scalar(statement)


def get_fiscal_year_by_name(
    db: Session,
    company_id: int,
    name: str,
) -> FiscalYear | None:
    statement = select(FiscalYear).where(
        FiscalYear.company_id == company_id,
        FiscalYear.name == name.strip(),
    )
    return db.scalar(statement)


def list_fiscal_years(
    db: Session,
    company_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[FiscalYear]:
    statement = select(FiscalYear).order_by(FiscalYear.start_date.desc())

    if company_id is not None:
        statement = statement.where(FiscalYear.company_id == company_id)

    statement = statement.offset(skip).limit(limit)

    return list(db.scalars(statement).all())


def count_fiscal_years(
    db: Session,
    company_id: int | None = None,
) -> int:
    statement = select(func.count()).select_from(FiscalYear)

    if company_id is not None:
        statement = statement.where(FiscalYear.company_id == company_id)

    return int(db.scalar(statement) or 0)


def update_fiscal_year(
    db: Session,
    fiscal_year: FiscalYear,
    payload: FiscalYearUpdate,
) -> FiscalYear:
    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()

    for field, value in update_data.items():
        setattr(fiscal_year, field, value)

    db.add(fiscal_year)
    db.commit()
    db.refresh(fiscal_year)

    return fiscal_year


def find_fiscal_year_for_date(
    db: Session,
    company_id: int,
    entry_date: date,
) -> FiscalYear | None:
    statement = select(FiscalYear).where(
        FiscalYear.company_id == company_id,
        FiscalYear.start_date <= entry_date,
        FiscalYear.end_date >= entry_date,
    )
    return db.scalar(statement)


# -------------------------
# Fiscal Periods
# -------------------------

def create_fiscal_period(db: Session, payload: FiscalPeriodCreate) -> FiscalPeriod:
    fiscal_period = FiscalPeriod(
        company_id=payload.company_id,
        fiscal_year_id=payload.fiscal_year_id,
        period_no=payload.period_no,
        name=payload.name.strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
    )

    db.add(fiscal_period)
    db.commit()
    db.refresh(fiscal_period)

    return fiscal_period


def get_fiscal_period(db: Session, fiscal_period_id: int) -> FiscalPeriod | None:
    statement = select(FiscalPeriod).where(FiscalPeriod.id == fiscal_period_id)
    return db.scalar(statement)


def get_fiscal_period_by_no(
    db: Session,
    fiscal_year_id: int,
    period_no: int,
) -> FiscalPeriod | None:
    statement = select(FiscalPeriod).where(
        FiscalPeriod.fiscal_year_id == fiscal_year_id,
        FiscalPeriod.period_no == period_no,
    )
    return db.scalar(statement)


def get_fiscal_period_by_name(
    db: Session,
    fiscal_year_id: int,
    name: str,
) -> FiscalPeriod | None:
    statement = select(FiscalPeriod).where(
        FiscalPeriod.fiscal_year_id == fiscal_year_id,
        FiscalPeriod.name == name.strip(),
    )
    return db.scalar(statement)


def list_fiscal_periods(
    db: Session,
    company_id: int | None = None,
    fiscal_year_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[FiscalPeriod]:
    statement = select(FiscalPeriod).order_by(
        FiscalPeriod.fiscal_year_id.asc(),
        FiscalPeriod.period_no.asc(),
    )

    if company_id is not None:
        statement = statement.where(FiscalPeriod.company_id == company_id)

    if fiscal_year_id is not None:
        statement = statement.where(FiscalPeriod.fiscal_year_id == fiscal_year_id)

    statement = statement.offset(skip).limit(limit)

    return list(db.scalars(statement).all())


def count_fiscal_periods(
    db: Session,
    company_id: int | None = None,
    fiscal_year_id: int | None = None,
) -> int:
    statement = select(func.count()).select_from(FiscalPeriod)

    if company_id is not None:
        statement = statement.where(FiscalPeriod.company_id == company_id)

    if fiscal_year_id is not None:
        statement = statement.where(FiscalPeriod.fiscal_year_id == fiscal_year_id)

    return int(db.scalar(statement) or 0)


def update_fiscal_period(
    db: Session,
    fiscal_period: FiscalPeriod,
    payload: FiscalPeriodUpdate,
) -> FiscalPeriod:
    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()

    for field, value in update_data.items():
        setattr(fiscal_period, field, value)

    db.add(fiscal_period)
    db.commit()
    db.refresh(fiscal_period)

    return fiscal_period


def find_fiscal_period_for_date(
    db: Session,
    company_id: int,
    entry_date: date,
) -> FiscalPeriod | None:
    statement = select(FiscalPeriod).where(
        FiscalPeriod.company_id == company_id,
        FiscalPeriod.start_date <= entry_date,
        FiscalPeriod.end_date >= entry_date,
    )
    return db.scalar(statement)