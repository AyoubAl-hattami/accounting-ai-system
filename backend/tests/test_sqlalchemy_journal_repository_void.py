from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from app.application.journals.dto import JournalEntryDTO, VoidJournalEntryCommand
from app.infrastructure.database.sqlalchemy.repositories.journal_repository import (
    SqlAlchemyJournalRepository,
)
from app.modules.accounting.models.journal_entry import JournalEntry


def _entry():
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=31, company_id=3, fiscal_year_id=4, fiscal_period_id=5,
        entry_no="JE-31", entry_date=date(2026, 1, 2), description="unchanged",
        status="draft", source_type="manual", source_id=None,
        created_by_user_id=7, creator_name="Creator", reversal_of_id=None,
        posted_at=None, created_at=now, updated_at=now, lines=[],
    )


class RecordingSession:
    def __init__(self, entry=None):
        self.entry = entry
        self.original_status = entry.status if entry else None
        self.added = []
        self.flush_calls = self.rollback_calls = self.commit_calls = 0
        self.fail_flush = False

    def get(self, model, entity_id):
        assert model is JournalEntry
        return self.entry if self.entry and self.entry.id == entity_id else None

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flush_calls += 1
        if self.fail_flush:
            raise RuntimeError("void flush failed")

    def rollback(self):
        self.rollback_calls += 1
        self.entry.status = self.original_status


def test_repository_voids_flushes_and_never_commits():
    entry = _entry()
    db = RecordingSession(entry)

    result = SqlAlchemyJournalRepository(db).void(
        VoidJournalEntryCommand(journal_entry_id=31)
    )

    assert isinstance(result, JournalEntryDTO)
    assert result.status == "void"
    assert result.entry_no == "JE-31"
    assert result.creator_name == "Creator"
    assert entry.status == "void"
    assert db.added == [entry]
    assert db.flush_calls == 1
    assert db.rollback_calls == 0
    assert db.commit_calls == 0


def test_repository_void_failure_rolls_back_and_recovers():
    entry = _entry()
    db = RecordingSession(entry)
    repository = SqlAlchemyJournalRepository(db)
    command = VoidJournalEntryCommand(journal_entry_id=31)
    db.fail_flush = True

    with pytest.raises(RuntimeError, match="void flush failed"):
        repository.void(command)

    assert entry.status == "draft"
    assert db.rollback_calls == 1
    assert db.commit_calls == 0
    db.fail_flush = False
    assert repository.void(command).status == "void"
    assert db.commit_calls == 0


def test_repository_void_missing_id_is_internal_invariant_failure():
    db = RecordingSession()
    with pytest.raises(RuntimeError, match="disappeared before voiding"):
        SqlAlchemyJournalRepository(db).void(
            VoidJournalEntryCommand(journal_entry_id=404)
        )
    assert db.flush_calls == 0
    assert db.commit_calls == 0