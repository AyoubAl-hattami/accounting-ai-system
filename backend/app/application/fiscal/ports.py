"""Application ports for fiscal persistence."""

from typing import Protocol

from app.application.fiscal.dto import (
    CreateFiscalPeriodCommand,
    CreateFiscalYearCommand,
    FiscalPeriodDTO,
    FiscalYearDTO,
    UpdateFiscalPeriodCommand,
    UpdateFiscalYearCommand,
)


class FiscalRepository(Protocol):
    def create_year(self, command: CreateFiscalYearCommand) -> FiscalYearDTO:
        ...

    def update_year(self, command: UpdateFiscalYearCommand) -> FiscalYearDTO:
        ...

    def get_year_by_id(self, fiscal_year_id: int) -> FiscalYearDTO | None:
        ...

    def list_years(
        self,
        company_id: int,
        skip: int,
        limit: int,
    ) -> list[FiscalYearDTO]:
        ...

    def count_years(self, company_id: int) -> int:
        ...

    def create_period(self, command: CreateFiscalPeriodCommand) -> FiscalPeriodDTO:
        ...

    def update_period(self, command: UpdateFiscalPeriodCommand) -> FiscalPeriodDTO:
        ...

    def get_period_by_id(self, fiscal_period_id: int) -> FiscalPeriodDTO | None:
        ...

    def list_periods(
        self,
        company_id: int,
        fiscal_year_id: int | None,
        skip: int,
        limit: int,
    ) -> list[FiscalPeriodDTO]:
        ...

    def count_periods(
        self,
        company_id: int,
        fiscal_year_id: int | None,
    ) -> int:
        ...
