"""Fiscal application use cases."""

from datetime import date

from app.application.fiscal.dto import (
    CreateFiscalPeriodCommand,
    CreateFiscalYearCommand,
    FiscalPeriodDTO,
    FiscalPeriodPageDTO,
    FiscalYearDTO,
    FiscalYearPageDTO,
    UpdateFiscalPeriodCommand,
    UpdateFiscalYearCommand,
)
from app.application.fiscal.ports import FiscalRepository


class CreateFiscalYear:
    def __init__(self, repository: FiscalRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateFiscalYearCommand) -> FiscalYearDTO:
        normalized = CreateFiscalYearCommand(
            company_id=command.company_id,
            name=command.name.strip(),
            start_date=command.start_date,
            end_date=command.end_date,
            status=command.status,
        )
        return self._repository.create_year(normalized)


class UpdateFiscalYear:
    def __init__(self, repository: FiscalRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateFiscalYearCommand) -> FiscalYearDTO:
        normalized = UpdateFiscalYearCommand(
            fiscal_year_id=command.fiscal_year_id,
            name=(
                command.name.strip()
                if "name" in command.fields and command.name
                else command.name
            ),
            start_date=command.start_date,
            end_date=command.end_date,
            status=command.status,
            fields=command.fields,
        )
        return self._repository.update_year(normalized)


class GetFiscalYear:
    def __init__(self, repository: FiscalRepository) -> None:
        self._repository = repository

    def execute(self, fiscal_year_id: int) -> FiscalYearDTO | None:
        return self._repository.get_year_by_id(fiscal_year_id)


class FindFiscalYearForDate:
    def __init__(self, repository: FiscalRepository) -> None:
        self._repository = repository

    def execute(
        self,
        company_id: int,
        entry_date: date,
    ) -> FiscalYearDTO | None:
        return self._repository.find_year_for_date(company_id, entry_date)


class ListFiscalYears:
    def __init__(self, repository: FiscalRepository) -> None:
        self._repository = repository

    def execute(self, company_id: int, skip: int, limit: int) -> FiscalYearPageDTO:
        return FiscalYearPageDTO(
            items=self._repository.list_years(company_id, skip, limit),
            total=self._repository.count_years(company_id),
            skip=skip,
            limit=limit,
        )


class CreateFiscalPeriod:
    def __init__(self, repository: FiscalRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateFiscalPeriodCommand) -> FiscalPeriodDTO:
        normalized = CreateFiscalPeriodCommand(
            company_id=command.company_id,
            fiscal_year_id=command.fiscal_year_id,
            period_no=command.period_no,
            name=command.name.strip(),
            start_date=command.start_date,
            end_date=command.end_date,
            status=command.status,
        )
        return self._repository.create_period(normalized)


class UpdateFiscalPeriod:
    def __init__(self, repository: FiscalRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateFiscalPeriodCommand) -> FiscalPeriodDTO:
        normalized = UpdateFiscalPeriodCommand(
            fiscal_period_id=command.fiscal_period_id,
            period_no=command.period_no,
            name=(
                command.name.strip()
                if "name" in command.fields and command.name
                else command.name
            ),
            start_date=command.start_date,
            end_date=command.end_date,
            status=command.status,
            fields=command.fields,
        )
        return self._repository.update_period(normalized)


class GetFiscalPeriod:
    def __init__(self, repository: FiscalRepository) -> None:
        self._repository = repository

    def execute(self, fiscal_period_id: int) -> FiscalPeriodDTO | None:
        return self._repository.get_period_by_id(fiscal_period_id)


class FindFiscalPeriodForDate:
    def __init__(self, repository: FiscalRepository) -> None:
        self._repository = repository

    def execute(
        self,
        company_id: int,
        entry_date: date,
    ) -> FiscalPeriodDTO | None:
        return self._repository.find_period_for_date(company_id, entry_date)


class ListFiscalPeriods:
    def __init__(self, repository: FiscalRepository) -> None:
        self._repository = repository

    def execute(
        self,
        company_id: int,
        fiscal_year_id: int | None,
        skip: int,
        limit: int,
    ) -> FiscalPeriodPageDTO:
        return FiscalPeriodPageDTO(
            items=self._repository.list_periods(
                company_id, fiscal_year_id, skip, limit
            ),
            total=self._repository.count_periods(company_id, fiscal_year_id),
            skip=skip,
            limit=limit,
        )
