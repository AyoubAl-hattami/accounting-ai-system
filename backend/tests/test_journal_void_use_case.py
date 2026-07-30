from datetime import date, datetime, timezone

from app.application.journals.dto import JournalEntryDTO, VoidJournalEntryCommand
from app.application.journals.use_cases import VoidJournalEntry


class RecordingRepository:
    def __init__(self, result):
        self.result = result
        self.command = None

    def void(self, command):
        self.command = command
        return self.result


def test_void_journal_entry_delegates_command_and_returns_dto():
    now = datetime.now(timezone.utc)
    expected = JournalEntryDTO(
        id=31, company_id=3, fiscal_year_id=4, fiscal_period_id=5,
        entry_no="JE-31", entry_date=date(2026, 1, 2), description=None,
        status="void", source_type=None, source_id=None,
        created_by_user_id=7, creator_name="Creator", reversal_of_id=None,
        posted_at=None, created_at=now, updated_at=now, lines=[],
    )
    repository = RecordingRepository(expected)
    command = VoidJournalEntryCommand(journal_entry_id=31)

    result = VoidJournalEntry(repository).execute(command)

    assert result is expected
    assert repository.command is command
    assert repository.command.journal_entry_id == 31