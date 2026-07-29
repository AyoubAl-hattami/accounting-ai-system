from datetime import date, datetime, timezone

from app.application.journals.dto import JournalEntryDTO, ReviewJournalEntryCommand
from app.application.journals.use_cases import ReviewJournalEntry


class RecordingJournalRepository:
    def __init__(self, result: JournalEntryDTO) -> None:
        self.result = result
        self.command = None

    def review(self, command: ReviewJournalEntryCommand) -> JournalEntryDTO:
        self.command = command
        return self.result


def test_review_journal_entry_passes_command_and_returns_repository_dto():
    now = datetime.now(timezone.utc)
    expected = JournalEntryDTO(
        id=17,
        company_id=3,
        fiscal_year_id=4,
        fiscal_period_id=5,
        entry_no="JE-17",
        entry_date=date(2026, 1, 2),
        description=None,
        status="reviewed",
        source_type=None,
        source_id=None,
        created_by_user_id=7,
        creator_name="Creator",
        reversal_of_id=None,
        posted_at=None,
        created_at=now,
        updated_at=now,
        lines=[],
    )
    repository = RecordingJournalRepository(expected)
    command = ReviewJournalEntryCommand(journal_entry_id=17)

    result = ReviewJournalEntry(repository).execute(command)

    assert result is expected
    assert repository.command is command
    assert repository.command.journal_entry_id == 17