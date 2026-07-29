from datetime import date, datetime, timezone
from decimal import Decimal

from app.application.journals.dto import (
    CreateJournalEntryCommand,
    CreateJournalLineCommand,
    JournalEntryDTO,
)
from app.application.journals.use_cases import CreateJournalEntry


class RecordingJournalRepository:
    def __init__(self, result: JournalEntryDTO) -> None:
        self.result = result
        self.command = None

    def create(self, command: CreateJournalEntryCommand) -> JournalEntryDTO:
        self.command = command
        return self.result


def _result() -> JournalEntryDTO:
    now = datetime.now(timezone.utc)
    return JournalEntryDTO(
        id=11,
        company_id=3,
        fiscal_year_id=4,
        fiscal_period_id=5,
        entry_no="JE-11",
        entry_date=date(2026, 1, 2),
        description=" unchanged ",
        status="draft",
        source_type="manual",
        source_id="source-1",
        created_by_user_id=7,
        creator_name="Creator",
        reversal_of_id=None,
        posted_at=None,
        created_at=now,
        updated_at=now,
        lines=[],
    )


def test_create_journal_entry_trims_number_and_returns_repository_dto():
    expected = _result()
    repository = RecordingJournalRepository(expected)
    lines = (
        CreateJournalLineCommand(
            account_id=10,
            debit=Decimal("25.00"),
            credit=Decimal("0.00"),
            description=" debit unchanged ",
        ),
        CreateJournalLineCommand(
            account_id=20,
            debit=Decimal("0.00"),
            credit=Decimal("25.00"),
            description=None,
        ),
    )
    command = CreateJournalEntryCommand(
        company_id=3,
        fiscal_year_id=4,
        fiscal_period_id=5,
        entry_no="  JE-11  ",
        entry_date=date(2026, 1, 2),
        description=" unchanged ",
        source_type="manual",
        source_id="source-1",
        created_by_user_id=7,
        lines=lines,
    )

    result = CreateJournalEntry(repository).execute(command)

    assert result is expected
    assert repository.command == CreateJournalEntryCommand(
        company_id=3,
        fiscal_year_id=4,
        fiscal_period_id=5,
        entry_no="JE-11",
        entry_date=date(2026, 1, 2),
        description=" unchanged ",
        source_type="manual",
        source_id="source-1",
        created_by_user_id=7,
        lines=lines,
    )
    assert command.entry_no == "  JE-11  "
