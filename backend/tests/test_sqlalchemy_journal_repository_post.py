from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from app.application.journals.dto import JournalEntryDTO, PostJournalEntryCommand
from app.infrastructure.database.sqlalchemy.repositories.journal_repository import (
    SqlAlchemyJournalRepository,
)
from app.modules.accounting.models.journal_entry import JournalEntry


def _entry(entry_id, status, reversal_of_id=None):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=entry_id, company_id=3, fiscal_year_id=4, fiscal_period_id=5,
        entry_no=f"JE-{entry_id}", entry_date=date(2026, 1, 2),
        description=None, status=status, source_type=None, source_id=None,
        created_by_user_id=7, creator_name="Creator",
        reversal_of_id=reversal_of_id, posted_at=None,
        created_at=now, updated_at=now, lines=[],
    )


class RecordingSession:
    def __init__(self, *entries):
        self.entries = {entry.id: entry for entry in entries}
        self.original = {
            entry.id: (entry.status, entry.posted_at) for entry in entries
        }
        self.added = []
        self.flush_calls = self.rollback_calls = self.commit_calls = 0
        self.fail_flush = False

    def get(self, model, entity_id):
        assert model is JournalEntry
        return self.entries.get(entity_id)

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flush_calls += 1
        if self.fail_flush:
            raise RuntimeError("post flush failed")

    def rollback(self):
        self.rollback_calls += 1
        for entry_id, (status, posted_at) in self.original.items():
            self.entries[entry_id].status = status
            self.entries[entry_id].posted_at = posted_at


def test_repository_posts_reversal_and_marks_original_reversed_without_commit():
    original = _entry(20, "posted")
    reversal = _entry(21, "reviewed", reversal_of_id=20)
    db = RecordingSession(original, reversal)

    result = SqlAlchemyJournalRepository(db).post(
        PostJournalEntryCommand(journal_entry_id=21)
    )

    assert isinstance(result, JournalEntryDTO)
    assert result.status == "posted"
    assert result.posted_at is not None
    assert result.posted_at.tzinfo == timezone.utc
    assert reversal.status == "posted"
    assert original.status == "reversed"
    assert db.added == [original, reversal]
    assert db.flush_calls == 1
    assert db.rollback_calls == 0
    assert db.commit_calls == 0


def test_repository_post_failure_rolls_back_both_rows_and_recovers():
    original = _entry(20, "posted")
    reversal = _entry(21, "reviewed", reversal_of_id=20)
    db = RecordingSession(original, reversal)
    repository = SqlAlchemyJournalRepository(db)
    command = PostJournalEntryCommand(journal_entry_id=21)
    db.fail_flush = True

    with pytest.raises(RuntimeError, match="post flush failed"):
        repository.post(command)

    assert reversal.status == "reviewed"
    assert reversal.posted_at is None
    assert original.status == "posted"
    assert db.rollback_calls == 1
    assert db.commit_calls == 0
    db.fail_flush = False
    recovered = repository.post(command)
    assert recovered.status == "posted"
    assert original.status == "reversed"
    assert db.commit_calls == 0


def test_repository_post_missing_id_is_internal_invariant_failure():
    db = RecordingSession()
    with pytest.raises(RuntimeError, match="disappeared before posting"):
        SqlAlchemyJournalRepository(db).post(
            PostJournalEntryCommand(journal_entry_id=404)
        )
    assert db.flush_calls == 0
    assert db.commit_calls == 0