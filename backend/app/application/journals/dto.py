"""Framework-neutral DTOs for journal read use cases."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class JournalLineDTO:
    id: int
    journal_entry_id: int
    company_id: int
    account_id: int
    line_no: int
    debit: Decimal
    credit: Decimal
    description: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class JournalEntryDTO:
    id: int
    company_id: int
    fiscal_year_id: int
    fiscal_period_id: int
    entry_no: str
    entry_date: date
    description: str | None
    status: str
    source_type: str | None
    source_id: str | None
    created_by_user_id: int | None
    creator_name: str | None
    reversal_of_id: int | None
    posted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    lines: list[JournalLineDTO]


@dataclass(frozen=True, slots=True)
class JournalEntryPageDTO:
    items: list[JournalEntryDTO]
    total: int
    skip: int
    limit: int
