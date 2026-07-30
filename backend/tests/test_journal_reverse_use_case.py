from datetime import date, datetime, timezone

from app.application.journals.dto import JournalEntryDTO, ReverseJournalEntryCommand
from app.application.journals.use_cases import ReverseJournalEntry


class RecordingRepository:
    def __init__(self, result):
        self.result = result
        self.command = None

    def reverse(self, command):
        self.command = command
        return self.result


def test_reverse_journal_entry_trims_number_and_preserves_other_values():
    now = datetime.now(timezone.utc)
    expected = JournalEntryDTO(
        id=41, company_id=3, fiscal_year_id=4, fiscal_period_id=5,
        entry_no="REV-41", entry_date=date(2026, 1, 2),
        description=" custom ", status="draft", source_type="reversal",
        source_id="40", created_by_user_id=7, creator_name="Creator",
        reversal_of_id=40, posted_at=None, created_at=now,
        updated_at=now, lines=[],
    )
    repository = RecordingRepository(expected)
    command = ReverseJournalEntryCommand(
        original_entry_id=40, fiscal_year_id=4, fiscal_period_id=5,
        entry_no="  REV-41  ", entry_date=date(2026, 1, 2),
        description=" custom ", created_by_user_id=7,
    )

    result = ReverseJournalEntry(repository).execute(command)

    assert result is expected
    assert repository.command == ReverseJournalEntryCommand(
        original_entry_id=40, fiscal_year_id=4, fiscal_period_id=5,
        entry_no="REV-41", entry_date=date(2026, 1, 2),
        description=" custom ", created_by_user_id=7,
    )
    assert command.entry_no == "  REV-41  "