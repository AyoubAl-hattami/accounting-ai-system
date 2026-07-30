"""Narrow Clean Architecture facade for AI accounting consumers."""

from datetime import date

from sqlalchemy.orm import Session

from app.application.accounts.dto import AccountDTO
from app.application.accounts.use_cases import GetAccount
from app.application.fiscal.dto import FiscalPeriodDTO, FiscalYearDTO
from app.application.fiscal.use_cases import (
    FindFiscalPeriodForDate,
    FindFiscalYearForDate,
)
from app.application.journals.dto import (
    CreateJournalEntryCommand,
    JournalEntryDTO,
)
from app.application.journals.use_cases import (
    CountJournalEntries,
    CreateJournalEntry,
    GetJournalEntryByNo,
)
from app.infrastructure.database.sqlalchemy.repositories.account_repository import (
    SqlAlchemyAccountRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.fiscal_repository import (
    SqlAlchemyFiscalRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.journal_repository import (
    SqlAlchemyJournalRepository,
)


def list_accounts(
    db: Session,
    company_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[AccountDTO]:
    return SqlAlchemyAccountRepository(db).list_by_company(
        company_id=company_id,
        skip=skip,
        limit=limit,
    )


def get_account(db: Session, account_id: int) -> AccountDTO | None:
    return GetAccount(SqlAlchemyAccountRepository(db)).execute(account_id)


def list_journal_entries(
    db: Session,
    company_id: int,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[JournalEntryDTO]:
    return SqlAlchemyJournalRepository(db).list_by_company(
        company_id=company_id,
        status=status,
        skip=skip,
        limit=limit,
    )


def count_journal_entries(
    db: Session,
    company_id: int,
    status: str | None = None,
) -> int:
    return CountJournalEntries(SqlAlchemyJournalRepository(db)).execute(
        company_id=company_id,
        status=status,
    )


def get_journal_entry_by_no(
    db: Session,
    company_id: int,
    entry_no: str,
) -> JournalEntryDTO | None:
    return GetJournalEntryByNo(SqlAlchemyJournalRepository(db)).execute(
        company_id=company_id,
        entry_no=entry_no,
    )


def create_journal_entry(
    db: Session,
    command: CreateJournalEntryCommand,
) -> JournalEntryDTO:
    return CreateJournalEntry(SqlAlchemyJournalRepository(db)).execute(command)


def find_fiscal_year_for_date(
    db: Session,
    company_id: int,
    entry_date: date,
) -> FiscalYearDTO | None:
    return FindFiscalYearForDate(SqlAlchemyFiscalRepository(db)).execute(
        company_id=company_id,
        entry_date=entry_date,
    )


def find_fiscal_period_for_date(
    db: Session,
    company_id: int,
    entry_date: date,
) -> FiscalPeriodDTO | None:
    return FindFiscalPeriodForDate(SqlAlchemyFiscalRepository(db)).execute(
        company_id=company_id,
        entry_date=entry_date,
    )


def list_fiscal_periods(
    db: Session,
    company_id: int,
    fiscal_year_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[FiscalPeriodDTO]:
    return SqlAlchemyFiscalRepository(db).list_periods(
        company_id=company_id,
        fiscal_year_id=fiscal_year_id,
        skip=skip,
        limit=limit,
    )
