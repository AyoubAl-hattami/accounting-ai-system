from datetime import date, datetime, timezone

from app.application.journals.dto import JournalEntryDTO, UpdateJournalEntryCommand
from app.application.journals.use_cases import UpdateJournalEntry


class RecordingJournalRepository:
    def __init__(self, result: JournalEntryDTO) -> None:
        self.result = result
        self.command = None

    def update(self, command: UpdateJournalEntryCommand) -> JournalEntryDTO:
        self.command = command
        return self.result


def _result() -> JournalEntryDTO:
    now = datetime.now(timezone.utc)
    return JournalEntryDTO(
        id=14,
        company_id=3,
        fiscal_year_id=4,
        fiscal_period_id=5,
        entry_no="JE-14",
        entry_date=date(2026, 1, 2),
        description=None,
        status="draft",
        source_type=None,
        source_id="preserved",
        created_by_user_id=7,
        creator_name="Creator",
        reversal_of_id=None,
        posted_at=None,
        created_at=now,
        updated_at=now,
        lines=[],
    )


def test_update_journal_entry_preserves_command_and_returns_repository_dto():
    expected = _result()
    repository = RecordingJournalRepository(expected)
    command = UpdateJournalEntryCommand(
        journal_entry_id=14,
        description=None,
        source_type=None,
        source_id="omitted-value",
        fiscal_year_id=8,
        fiscal_period_id=9,
        fields=frozenset({"description", "source_type"}),
    )

    result = UpdateJournalEntry(repository).execute(command)

    assert result is expected
    assert repository.command is command
    assert repository.command.journal_entry_id == 14
    assert repository.command.description is None
    assert repository.command.source_type is None
    assert repository.command.fields == frozenset({"description", "source_type"})
    assert "source_id" not in repository.command.fields