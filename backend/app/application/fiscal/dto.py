"""Framework-neutral DTOs and commands for fiscal use cases."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class CreateFiscalYearCommand:
    company_id: int
    name: str
    start_date: date
    end_date: date
    status: str


@dataclass(frozen=True, slots=True)
class UpdateFiscalYearCommand:
    fiscal_year_id: int
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class FiscalYearDTO:
    id: int
    company_id: int
    name: str
    start_date: date
    end_date: date
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class FiscalYearPageDTO:
    items: list[FiscalYearDTO]
    total: int
    skip: int
    limit: int


@dataclass(frozen=True, slots=True)
class CreateFiscalPeriodCommand:
    company_id: int
    fiscal_year_id: int
    period_no: int
    name: str
    start_date: date
    end_date: date
    status: str


@dataclass(frozen=True, slots=True)
class UpdateFiscalPeriodCommand:
    fiscal_period_id: int
    period_no: int | None = None
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class FiscalPeriodDTO:
    id: int
    company_id: int
    fiscal_year_id: int
    period_no: int
    name: str
    start_date: date
    end_date: date
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class FiscalPeriodPageDTO:
    items: list[FiscalPeriodDTO]
    total: int
    skip: int
    limit: int
