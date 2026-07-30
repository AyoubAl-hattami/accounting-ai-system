from datetime import date, datetime, timezone

from app.application.fiscal.dto import (
    CreateFiscalPeriodCommand,
    CreateFiscalYearCommand,
    FiscalPeriodDTO,
    FiscalYearDTO,
    UpdateFiscalPeriodCommand,
    UpdateFiscalYearCommand,
)
from app.application.fiscal.use_cases import (
    CreateFiscalPeriod,
    CreateFiscalYear,
    FindFiscalPeriodForDate,
    FindFiscalYearForDate,
    GetFiscalPeriod,
    GetFiscalYear,
    ListFiscalPeriods,
    ListFiscalYears,
    UpdateFiscalPeriod,
    UpdateFiscalYear,
)


class FakeFiscalRepository:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.year = FiscalYearDTO(
            3, 7, "FY 2200", date(2200, 1, 1), date(2200, 12, 31),
            "open", now, now,
        )
        self.period = FiscalPeriodDTO(
            5, 7, 3, 1, "January", date(2200, 1, 1), date(2200, 1, 31),
            "open", now, now,
        )
        self.calls: list[tuple[str, object]] = []

    def create_year(self, command):
        self.calls.append(("create_year", command))
        return self.year

    def update_year(self, command):
        self.calls.append(("update_year", command))
        return self.year

    def get_year_by_id(self, fiscal_year_id):
        self.calls.append(("get_year", fiscal_year_id))
        return self.year

    def find_year_for_date(self, company_id, entry_date):
        self.calls.append(("find_year", (company_id, entry_date)))
        return self.year

    def list_years(self, company_id, skip, limit):
        self.calls.append(("list_years", (company_id, skip, limit)))
        return [self.year]

    def count_years(self, company_id):
        self.calls.append(("count_years", company_id))
        return 1

    def create_period(self, command):
        self.calls.append(("create_period", command))
        return self.period

    def update_period(self, command):
        self.calls.append(("update_period", command))
        return self.period

    def get_period_by_id(self, fiscal_period_id):
        self.calls.append(("get_period", fiscal_period_id))
        return self.period

    def find_period_for_date(self, company_id, entry_date):
        self.calls.append(("find_period", (company_id, entry_date)))
        return self.period

    def list_periods(self, company_id, fiscal_year_id, skip, limit):
        self.calls.append(
            ("list_periods", (company_id, fiscal_year_id, skip, limit))
        )
        return [self.period]

    def count_periods(self, company_id, fiscal_year_id):
        self.calls.append(("count_periods", (company_id, fiscal_year_id)))
        return 1


def test_fiscal_year_use_cases_normalize_and_delegate():
    repository = FakeFiscalRepository()
    create = CreateFiscalYearCommand(
        7, "  FY 2200  ", date(2200, 1, 1), date(2200, 12, 31), "open"
    )
    fields = frozenset({"name", "status"})
    update = UpdateFiscalYearCommand(
        fiscal_year_id=3, name="  Renamed  ", status="closed", fields=fields
    )

    assert CreateFiscalYear(repository).execute(create) is repository.year
    assert UpdateFiscalYear(repository).execute(update) is repository.year
    assert GetFiscalYear(repository).execute(3) is repository.year
    page = ListFiscalYears(repository).execute(7, 2, 10)

    assert repository.calls[0][1].name == "FY 2200"
    normalized_update = repository.calls[1][1]
    assert normalized_update.name == "Renamed"
    assert normalized_update.fields is fields
    assert page.items == [repository.year]
    assert (page.total, page.skip, page.limit) == (1, 2, 10)


def test_fiscal_period_use_cases_normalize_and_preserve_fields():
    repository = FakeFiscalRepository()
    create = CreateFiscalPeriodCommand(
        7, 3, 1, "  January  ", date(2200, 1, 1), date(2200, 1, 31), "open"
    )
    fields = frozenset({"name", "status"})
    update = UpdateFiscalPeriodCommand(
        fiscal_period_id=5, name="  Jan  ", status="locked", fields=fields
    )

    assert CreateFiscalPeriod(repository).execute(create) is repository.period
    assert UpdateFiscalPeriod(repository).execute(update) is repository.period
    assert GetFiscalPeriod(repository).execute(5) is repository.period
    page = ListFiscalPeriods(repository).execute(7, 3, 0, 20)

    assert repository.calls[0][1].name == "January"
    normalized_update = repository.calls[1][1]
    assert normalized_update.name == "Jan"
    assert normalized_update.fields is fields
    assert page.items == [repository.period]
    assert (page.total, page.skip, page.limit) == (1, 0, 20)


def test_fiscal_date_lookups_preserve_company_and_date():
    repository = FakeFiscalRepository()
    entry_date = date(2200, 1, 15)

    assert FindFiscalYearForDate(repository).execute(7, entry_date) is repository.year
    assert FindFiscalPeriodForDate(repository).execute(7, entry_date) is repository.period
    assert repository.calls == [
        ("find_year", (7, entry_date)),
        ("find_period", (7, entry_date)),
    ]
