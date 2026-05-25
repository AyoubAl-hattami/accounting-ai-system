from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.schemas.journal import (
    JournalEntryCreate,
    JournalEntryUpdate,
    JournalEntryReverseCreate,
)

def get_company_or_none(db: Session, company_id: int) -> Company | None:
    statement = select(Company).where(Company.id == company_id)
    return db.scalar(statement)


def get_account(db: Session, account_id: int) -> Account | None:
    statement = select(Account).where(Account.id == account_id)
    return db.scalar(statement)


def get_journal_entry(
    db: Session,
    journal_entry_id: int,
) -> JournalEntry | None:
    statement = (
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == journal_entry_id)
    )

    return db.scalar(statement)


def get_journal_entry_by_no(
    db: Session,
    company_id: int,
    entry_no: str,
) -> JournalEntry | None:
    statement = select(JournalEntry).where(
        JournalEntry.company_id == company_id,
        JournalEntry.entry_no == entry_no.strip(),
    )

    return db.scalar(statement)


def list_journal_entries(
    db: Session,
    company_id: int | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[JournalEntry]:
    statement = (
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc())
    )

    if company_id is not None:
        statement = statement.where(JournalEntry.company_id == company_id)

    if status is not None:
        statement = statement.where(JournalEntry.status == status)

    statement = statement.offset(skip).limit(limit)

    return list(db.scalars(statement).all())


def find_fiscal_year_for_date(
    db: Session,
    company_id: int,
    entry_date,
) -> FiscalYear | None:
    statement = select(FiscalYear).where(
        FiscalYear.company_id == company_id,
        FiscalYear.start_date <= entry_date,
        FiscalYear.end_date >= entry_date,
    )

    return db.scalar(statement)


def find_fiscal_period_for_date(
    db: Session,
    company_id: int,
    entry_date,
) -> FiscalPeriod | None:
    statement = select(FiscalPeriod).where(
        FiscalPeriod.company_id == company_id,
        FiscalPeriod.start_date <= entry_date,
        FiscalPeriod.end_date >= entry_date,
    )

    return db.scalar(statement)


def create_journal_entry(
    db: Session,
    payload: JournalEntryCreate,
    fiscal_year: FiscalYear,
    fiscal_period: FiscalPeriod,
) -> JournalEntry:
    journal_entry = JournalEntry(
        company_id=payload.company_id,
        fiscal_year_id=fiscal_year.id,
        fiscal_period_id=fiscal_period.id,
        entry_no=payload.entry_no.strip(),
        entry_date=payload.entry_date,
        description=payload.description,
        status="draft",
        source_type=payload.source_type,
        source_id=payload.source_id,
    )

    journal_entry.lines = [
        JournalLine(
            company_id=payload.company_id,
            account_id=line.account_id,
            line_no=index + 1,
            debit=line.debit,
            credit=line.credit,
            description=line.description,
        )
        for index, line in enumerate(payload.lines)
    ]

    db.add(journal_entry)
    db.commit()
    db.refresh(journal_entry)

    return get_journal_entry(db=db, journal_entry_id=journal_entry.id)


def update_journal_entry(
    db: Session,
    journal_entry: JournalEntry,
    payload: JournalEntryUpdate,
    fiscal_year: FiscalYear | None = None,
    fiscal_period: FiscalPeriod | None = None,
) -> JournalEntry:
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(journal_entry, field, value)

    if fiscal_year is not None:
        journal_entry.fiscal_year_id = fiscal_year.id

    if fiscal_period is not None:
        journal_entry.fiscal_period_id = fiscal_period.id

    db.add(journal_entry)
    db.commit()
    db.refresh(journal_entry)

    return get_journal_entry(db=db, journal_entry_id=journal_entry.id)
def calculate_journal_totals(journal_entry: JournalEntry) -> tuple[Decimal, Decimal]:
    total_debit = sum(
        (line.debit for line in journal_entry.lines),
        Decimal("0.00"),
    )

    total_credit = sum(
        (line.credit for line in journal_entry.lines),
        Decimal("0.00"),
    )

    return total_debit, total_credit


def mark_journal_entry_reviewed(
    db: Session,
    journal_entry: JournalEntry,
) -> JournalEntry:
    journal_entry.status = "reviewed"

    db.add(journal_entry)
    db.commit()
    db.refresh(journal_entry)

    return get_journal_entry(db=db, journal_entry_id=journal_entry.id)

def post_journal_entry(
    db: Session,
    journal_entry: JournalEntry,
) -> JournalEntry:
    journal_entry.status = "posted"
    journal_entry.posted_at = datetime.now(timezone.utc)

    if journal_entry.reversal_of_id is not None:
        original_entry = db.get(JournalEntry, journal_entry.reversal_of_id)

        if original_entry is not None:
            original_entry.status = "reversed"
            db.add(original_entry)

    db.add(journal_entry)
    db.commit()
    db.refresh(journal_entry)

    return get_journal_entry(db=db, journal_entry_id=journal_entry.id)
def reverse_journal_entry(
    db: Session,
    original_entry: JournalEntry,
    payload: JournalEntryReverseCreate,
    fiscal_year: FiscalYear,
    fiscal_period: FiscalPeriod,
) -> JournalEntry:
    reversal_entry = JournalEntry(
        company_id=original_entry.company_id,
        fiscal_year_id=fiscal_year.id,
        fiscal_period_id=fiscal_period.id,
        entry_no=payload.entry_no.strip(),
        entry_date=payload.entry_date,
        description=payload.description or f"Reversal of {original_entry.entry_no}",
        status="draft",
        source_type="reversal",
        source_id=str(original_entry.id),
        reversal_of_id=original_entry.id,
    )

    reversal_entry.lines = [
        JournalLine(
            company_id=original_entry.company_id,
            account_id=line.account_id,
            line_no=index + 1,
            debit=line.credit,
            credit=line.debit,
            description=f"Reversal: {line.description or original_entry.entry_no}",
        )
        for index, line in enumerate(original_entry.lines)
    ]

    db.add(reversal_entry)
    db.commit()
    db.refresh(reversal_entry)

    return get_journal_entry(db=db, journal_entry_id=reversal_entry.id)
def void_journal_entry(
    db: Session,
    journal_entry: JournalEntry,
) -> JournalEntry:
    journal_entry.status = "void"

    db.add(journal_entry)
    db.commit()
    db.refresh(journal_entry)

    return get_journal_entry(db=db, journal_entry_id=journal_entry.id)