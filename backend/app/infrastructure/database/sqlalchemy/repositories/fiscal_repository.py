"""SQLAlchemy implementation of the fiscal repository port."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.fiscal.dto import (
    CreateFiscalPeriodCommand,
    CreateFiscalYearCommand,
    FiscalPeriodDTO,
    FiscalYearDTO,
    UpdateFiscalPeriodCommand,
    UpdateFiscalYearCommand,
)
from app.application.fiscal.ports import FiscalRepository
from app.core.database import flush_or_rollback
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear


class SqlAlchemyFiscalRepository(FiscalRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _year_to_dto(fiscal_year: FiscalYear) -> FiscalYearDTO:
        return FiscalYearDTO(
            id=fiscal_year.id,
            company_id=fiscal_year.company_id,
            name=fiscal_year.name,
            start_date=fiscal_year.start_date,
            end_date=fiscal_year.end_date,
            status=fiscal_year.status,
            created_at=fiscal_year.created_at,
            updated_at=fiscal_year.updated_at,
        )

    @staticmethod
    def _period_to_dto(fiscal_period: FiscalPeriod) -> FiscalPeriodDTO:
        return FiscalPeriodDTO(
            id=fiscal_period.id,
            company_id=fiscal_period.company_id,
            fiscal_year_id=fiscal_period.fiscal_year_id,
            period_no=fiscal_period.period_no,
            name=fiscal_period.name,
            start_date=fiscal_period.start_date,
            end_date=fiscal_period.end_date,
            status=fiscal_period.status,
            created_at=fiscal_period.created_at,
            updated_at=fiscal_period.updated_at,
        )

    def create_year(self, command: CreateFiscalYearCommand) -> FiscalYearDTO:
        fiscal_year = FiscalYear(
            company_id=command.company_id,
            name=command.name,
            start_date=command.start_date,
            end_date=command.end_date,
            status=command.status,
        )
        self._db.add(fiscal_year)
        flush_or_rollback(self._db)
        return self._year_to_dto(fiscal_year)

    def update_year(self, command: UpdateFiscalYearCommand) -> FiscalYearDTO:
        fiscal_year = self._db.scalar(
            select(FiscalYear).where(FiscalYear.id == command.fiscal_year_id)
        )
        if fiscal_year is None:
            raise RuntimeError(
                f"Fiscal year {command.fiscal_year_id} disappeared before update staging"
            )
        for field in command.fields:
            setattr(fiscal_year, field, getattr(command, field))
        self._db.add(fiscal_year)
        flush_or_rollback(self._db)
        return self._year_to_dto(fiscal_year)

    def get_year_by_id(self, fiscal_year_id: int) -> FiscalYearDTO | None:
        fiscal_year = self._db.scalar(
            select(FiscalYear).where(FiscalYear.id == fiscal_year_id)
        )
        return self._year_to_dto(fiscal_year) if fiscal_year is not None else None

    def list_years(
        self,
        company_id: int,
        skip: int,
        limit: int,
    ) -> list[FiscalYearDTO]:
        statement = (
            select(FiscalYear)
            .where(FiscalYear.company_id == company_id)
            .order_by(FiscalYear.start_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return [self._year_to_dto(item) for item in self._db.scalars(statement).all()]

    def count_years(self, company_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(FiscalYear)
            .where(FiscalYear.company_id == company_id)
        )
        return int(self._db.scalar(statement) or 0)

    def create_period(self, command: CreateFiscalPeriodCommand) -> FiscalPeriodDTO:
        fiscal_period = FiscalPeriod(
            company_id=command.company_id,
            fiscal_year_id=command.fiscal_year_id,
            period_no=command.period_no,
            name=command.name,
            start_date=command.start_date,
            end_date=command.end_date,
            status=command.status,
        )
        self._db.add(fiscal_period)
        flush_or_rollback(self._db)
        return self._period_to_dto(fiscal_period)

    def update_period(self, command: UpdateFiscalPeriodCommand) -> FiscalPeriodDTO:
        fiscal_period = self._db.scalar(
            select(FiscalPeriod).where(FiscalPeriod.id == command.fiscal_period_id)
        )
        if fiscal_period is None:
            raise RuntimeError(
                f"Fiscal period {command.fiscal_period_id} disappeared before update staging"
            )
        for field in command.fields:
            setattr(fiscal_period, field, getattr(command, field))
        self._db.add(fiscal_period)
        flush_or_rollback(self._db)
        return self._period_to_dto(fiscal_period)

    def get_period_by_id(self, fiscal_period_id: int) -> FiscalPeriodDTO | None:
        fiscal_period = self._db.scalar(
            select(FiscalPeriod).where(FiscalPeriod.id == fiscal_period_id)
        )
        return self._period_to_dto(fiscal_period) if fiscal_period is not None else None

    def list_periods(
        self,
        company_id: int,
        fiscal_year_id: int | None,
        skip: int,
        limit: int,
    ) -> list[FiscalPeriodDTO]:
        statement = select(FiscalPeriod).where(FiscalPeriod.company_id == company_id)
        if fiscal_year_id is not None:
            statement = statement.where(FiscalPeriod.fiscal_year_id == fiscal_year_id)
        statement = (
            statement.order_by(
                FiscalPeriod.fiscal_year_id.asc(),
                FiscalPeriod.period_no.asc(),
            )
            .offset(skip)
            .limit(limit)
        )
        return [
            self._period_to_dto(item) for item in self._db.scalars(statement).all()
        ]

    def count_periods(
        self,
        company_id: int,
        fiscal_year_id: int | None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(FiscalPeriod)
            .where(FiscalPeriod.company_id == company_id)
        )
        if fiscal_year_id is not None:
            statement = statement.where(FiscalPeriod.fiscal_year_id == fiscal_year_id)
        return int(self._db.scalar(statement) or 0)
