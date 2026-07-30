"""Repository-backed lookup facade for accounting HTTP routes."""

from datetime import date

from sqlalchemy.orm import Session

from app.application.accounts.dto import AccountDTO
from app.application.fiscal.dto import FiscalPeriodDTO, FiscalYearDTO
from app.application.journals.dto import JournalEntryDTO
from app.infrastructure.database.sqlalchemy.repositories.account_repository import (
    SqlAlchemyAccountRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.fiscal_repository import (
    SqlAlchemyFiscalRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.journal_repository import (
    SqlAlchemyJournalRepository,
)
from app.modules.accounting.models.company import Company
from app.modules.accounting.services.company_service import get_company


def get_company_or_none(db: Session, company_id: int) -> Company | None:
    return get_company(db=db, company_id=company_id)


def get_account(db: Session, account_id: int) -> AccountDTO | None:
    return SqlAlchemyAccountRepository(db).get_by_id(account_id)


def get_account_by_code(db: Session, company_id: int, code: str) -> AccountDTO | None:
    return SqlAlchemyAccountRepository(db).get_by_code(company_id, code)


def get_fiscal_year(db: Session, fiscal_year_id: int) -> FiscalYearDTO | None:
    return SqlAlchemyFiscalRepository(db).get_year_by_id(fiscal_year_id)


def get_fiscal_year_by_name(
    db: Session,
    company_id: int,
    name: str,
) -> FiscalYearDTO | None:
    return SqlAlchemyFiscalRepository(db).get_year_by_name(company_id, name.strip())


def find_overlapping_fiscal_year(
    db: Session,
    company_id: int,
    start_date: date,
    end_date: date,
    exclude_fiscal_year_id: int | None = None,
) -> FiscalYearDTO | None:
    return SqlAlchemyFiscalRepository(db).find_overlapping_year(
        company_id,
        start_date,
        end_date,
        exclude_fiscal_year_id,
    )


def count_journal_entries_for_fiscal_year(db: Session, fiscal_year_id: int) -> int:
    return SqlAlchemyJournalRepository(db).count_by_fiscal_year(fiscal_year_id)


def get_fiscal_period_by_no(
    db: Session,
    fiscal_year_id: int,
    period_no: int,
) -> FiscalPeriodDTO | None:
    return SqlAlchemyFiscalRepository(db).get_period_by_no(fiscal_year_id, period_no)


def get_fiscal_period_by_name(
    db: Session,
    fiscal_year_id: int,
    name: str,
) -> FiscalPeriodDTO | None:
    return SqlAlchemyFiscalRepository(db).get_period_by_name(
        fiscal_year_id,
        name.strip(),
    )


def find_overlapping_fiscal_period(
    db: Session,
    company_id: int,
    fiscal_year_id: int,
    start_date: date,
    end_date: date,
    exclude_fiscal_period_id: int | None = None,
) -> FiscalPeriodDTO | None:
    return SqlAlchemyFiscalRepository(db).find_overlapping_period(
        company_id,
        fiscal_year_id,
        start_date,
        end_date,
        exclude_fiscal_period_id,
    )


def find_fiscal_year_for_date(
    db: Session,
    company_id: int,
    entry_date: date,
) -> FiscalYearDTO | None:
    return SqlAlchemyFiscalRepository(db).find_year_for_date(company_id, entry_date)


def find_fiscal_period_for_date(
    db: Session,
    company_id: int,
    entry_date: date,
) -> FiscalPeriodDTO | None:
    return SqlAlchemyFiscalRepository(db).find_period_for_date(company_id, entry_date)


def get_journal_entry(db: Session, journal_entry_id: int) -> JournalEntryDTO | None:
    return SqlAlchemyJournalRepository(db).get_by_id(journal_entry_id)


def get_journal_entry_by_no(
    db: Session,
    company_id: int,
    entry_no: str,
) -> JournalEntryDTO | None:
    return SqlAlchemyJournalRepository(db).get_by_entry_no(
        company_id,
        entry_no.strip(),
    )


def get_reversal_for_entry(
    db: Session,
    original_entry_id: int,
) -> JournalEntryDTO | None:
    return SqlAlchemyJournalRepository(db).get_reversal_by_original_id(original_entry_id)
