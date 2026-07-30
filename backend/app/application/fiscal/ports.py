"""Application ports for fiscal persistence."""

from datetime import date
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

    def get_year_by_name(
        self,
        company_id: int,
        name: str,
    ) -> FiscalYearDTO | None:
        ...

    def find_overlapping_year(
        self,
        company_id: int,
        start_date: date,
        end_date: date,
        exclude_fiscal_year_id: int | None,
    ) -> FiscalYearDTO | None:
        ...

    def find_year_for_date(
        self,
        company_id: int,
        entry_date: date,
    ) -> FiscalYearDTO | None:
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

    def get_period_by_no(
        self,
        fiscal_year_id: int,
        period_no: int,
    ) -> FiscalPeriodDTO | None:
        ...

    def get_period_by_name(
        self,
        fiscal_year_id: int,
        name: str,
    ) -> FiscalPeriodDTO | None:
        ...

    def find_overlapping_period(
        self,
        company_id: int,
        fiscal_year_id: int,
        start_date: date,
        end_date: date,
        exclude_fiscal_period_id: int | None,
    ) -> FiscalPeriodDTO | None:
        ...

    def find_period_for_date(
        self,
        company_id: int,
        entry_date: date,
    ) -> FiscalPeriodDTO | None:
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
