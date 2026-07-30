from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application.fiscal.dto import (
    CreateFiscalPeriodCommand,
    CreateFiscalYearCommand,
    FiscalPeriodDTO,
    FiscalYearDTO,
    UpdateFiscalPeriodCommand,
    UpdateFiscalYearCommand,
)
from app.infrastructure.database.sqlalchemy.repositories.fiscal_repository import (
    SqlAlchemyFiscalRepository,
)
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear


class CountingSession(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commit_calls = 0

    def commit(self):
        self.commit_calls += 1
        return super().commit()


def test_sqlalchemy_fiscal_repository_crud_lists_and_never_commits():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Company.__table__.create(engine)
    FiscalYear.__table__.create(engine)
    FiscalPeriod.__table__.create(engine)
    try:
        with CountingSession(engine) as db:
            first = Company(name="Fiscal First", base_currency="USD")
            second = Company(name="Fiscal Second", base_currency="USD")
            db.add_all([first, second])
            db.commit()
            db.commit_calls = 0
            repository = SqlAlchemyFiscalRepository(db)

            older = repository.create_year(
                CreateFiscalYearCommand(
                    first.id, "FY 2200", date(2200, 1, 1),
                    date(2200, 12, 31), "open",
                )
            )
            newer = repository.create_year(
                CreateFiscalYearCommand(
                    first.id, "FY 2201", date(2201, 1, 1),
                    date(2201, 12, 31), "open",
                )
            )
            other = repository.create_year(
                CreateFiscalYearCommand(
                    second.id, "FY 2200", date(2200, 1, 1),
                    date(2200, 12, 31), "open",
                )
            )

            assert isinstance(older, FiscalYearDTO)
            assert repository.get_year_by_id(other.id) == other
            assert repository.find_year_for_date(
                first.id, date(2200, 6, 1)
            ).id == older.id
            assert repository.find_year_for_date(
                second.id, date(2201, 6, 1)
            ) is None
            assert [item.id for item in repository.list_years(first.id, 0, 10)] == [
                newer.id, older.id,
            ]
            assert repository.count_years(first.id) == 2
            updated_year = repository.update_year(
                UpdateFiscalYearCommand(
                    fiscal_year_id=older.id,
                    name="Renamed",
                    fields=frozenset({"name"}),
                )
            )
            assert updated_year.name == "Renamed"
            assert updated_year.status == "open"

            period = repository.create_period(
                CreateFiscalPeriodCommand(
                    first.id, older.id, 1, "January", date(2200, 1, 1),
                    date(2200, 1, 31), "open",
                )
            )
            assert isinstance(period, FiscalPeriodDTO)
            assert repository.get_period_by_id(period.id) == period
            assert repository.find_period_for_date(
                first.id, date(2200, 1, 15)
            ).id == period.id
            assert repository.find_period_for_date(
                second.id, date(2200, 1, 15)
            ) is None
            assert repository.count_periods(first.id, older.id) == 1
            assert repository.count_periods(second.id, None) == 0
            updated_period = repository.update_period(
                UpdateFiscalPeriodCommand(
                    fiscal_period_id=period.id,
                    status="closed",
                    fields=frozenset({"status"}),
                )
            )
            assert updated_period.status == "closed"
            assert updated_period.name == "January"
            assert repository.list_periods(first.id, newer.id, 0, 10) == []
            assert db.commit_calls == 0
    finally:
        engine.dispose()
