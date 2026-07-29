from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.journals.dto import JournalEntryDTO, ReviewJournalEntryCommand
from app.infrastructure.database.sqlalchemy.repositories.journal_repository import (
    SqlAlchemyJournalRepository,
)
from app.modules.accounting.models.journal_entry import JournalEntry


class RecordingSession:
    def __init__(self, entry=None) -> None:
        self.entry = entry
        self.added = []
        self.flush_calls = 0
        self.rollback_calls = 0
        self.commit_calls = 0
        self.fail_flush = False
        self.original_status = entry.status if entry is not None else None

    def get(self, model, entity_id):
        assert model is JournalEntry
        if self.entry is not None and self.entry.id == entity_id:
            return self.entry
        return None

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flush_calls += 1
        if self.fail_flush:
            raise RuntimeError("flush failed")

    def rollback(self):
        self.rollback_calls += 1
        if self.entry is not None:
            self.entry.status = self.original_status


def _entry():
    now = datetime.now(timezone.utc)
    line = SimpleNamespace(
        id=21,
        journal_entry_id=17,
        company_id=3,
        account_id=10,
        line_no=1,
        debit=Decimal("19.00"),
        credit=Decimal("0.00"),
        description="unchanged line",
        created_at=now,
        updated_at=now,
    )
    return SimpleNamespace(
        id=17,
        company_id=3,
        fiscal_year_id=4,
        fiscal_period_id=5,
        entry_no="JE-17",
        entry_date=date(2026, 1, 2),
        description="unchanged entry",
        status="draft",
        source_type="manual",
        source_id=None,
        created_by_user_id=7,
        creator_name="Creator",
        reversal_of_id=None,
        posted_at=None,
        created_at=now,
        updated_at=now,
        lines=[line],
    )


def test_repository_stages_review_flushes_and_never_commits():
    entry = _entry()
    db = RecordingSession(entry)

    result = SqlAlchemyJournalRepository(db).review(
        ReviewJournalEntryCommand(journal_entry_id=17)
    )

    assert isinstance(result, JournalEntryDTO)
    assert result.status == "reviewed"
    assert result.entry_no == "JE-17"
    assert result.creator_name == "Creator"
    assert result.lines[0].account_id == 10
    assert result.lines[0].debit == Decimal("19.00")
    assert entry.status == "reviewed"
    assert db.added == [entry]
    assert db.flush_calls == 1
    assert db.rollback_calls == 0
    assert db.commit_calls == 0


def test_repository_review_flush_failure_rolls_back_and_recovers():
    entry = _entry()
    db = RecordingSession(entry)
    repository = SqlAlchemyJournalRepository(db)
    command = ReviewJournalEntryCommand(journal_entry_id=17)
    db.fail_flush = True

    with pytest.raises(RuntimeError, match="flush failed"):
        repository.review(command)

    assert entry.status == "draft"
    assert db.rollback_calls == 1
    assert db.commit_calls == 0
    db.fail_flush = False
    recovered = repository.review(command)
    assert recovered.status == "reviewed"
    assert db.commit_calls == 0


def test_repository_review_missing_id_is_internal_invariant_failure():
    db = RecordingSession()

    with pytest.raises(RuntimeError, match="disappeared before review"):
        SqlAlchemyJournalRepository(db).review(
            ReviewJournalEntryCommand(journal_entry_id=404)
        )

    assert db.flush_calls == 0
    assert db.commit_calls == 0