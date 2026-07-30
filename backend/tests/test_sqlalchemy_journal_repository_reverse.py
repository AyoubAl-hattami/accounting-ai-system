from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.journals.dto import JournalEntryDTO, ReverseJournalEntryCommand
from app.infrastructure.database.sqlalchemy.repositories.journal_repository import (
    SqlAlchemyJournalRepository,
)
from app.modules.accounting.models.journal_entry import JournalEntry


def _original():
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=40, company_id=3, entry_no="JE-40", status="posted",
        lines=[
            SimpleNamespace(
                account_id=10, debit=Decimal("55.00"),
                credit=Decimal("0.00"), description="debit line",
            ),
            SimpleNamespace(
                account_id=20, debit=Decimal("0.00"),
                credit=Decimal("55.00"), description=None,
            ),
        ], created_at=now, updated_at=now,
    )


class RecordingSession:
    def __init__(self, original=None):
        self.original = original
        self.added = []
        self.flush_calls = self.rollback_calls = self.commit_calls = 0
        self.fail_flush = False
        self.next_id = 100

    def get(self, model, entity_id):
        assert model is JournalEntry
        if self.original and self.original.id == entity_id:
            return self.original
        return None

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flush_calls += 1
        if self.fail_flush:
            raise RuntimeError("reverse flush failed")
        now = datetime.now(timezone.utc)
        for entry in self.added:
            if entry.id is None:
                entry.id = self.next_id
                self.next_id += 1
                entry.created_at = entry.updated_at = now
                for line in entry.lines:
                    line.id = self.next_id
                    self.next_id += 1
                    line.journal_entry_id = entry.id
                    line.created_at = line.updated_at = now

    def rollback(self):
        self.rollback_calls += 1
        self.added.clear()


def _command(description=None):
    return ReverseJournalEntryCommand(
        original_entry_id=40, fiscal_year_id=4, fiscal_period_id=5,
        entry_no="REV-40", entry_date=date(2026, 1, 2),
        description=description, created_by_user_id=7,
    )


def test_repository_stages_exact_reversal_lines_link_and_source_without_commit():
    db = RecordingSession(_original())

    result = SqlAlchemyJournalRepository(db).reverse(_command())

    assert isinstance(result, JournalEntryDTO)
    assert result.company_id == 3
    assert result.entry_no == "REV-40"
    assert result.description == "Reversal of JE-40"
    assert result.status == "draft"
    assert result.source_type == "reversal"
    assert result.source_id == "40"
    assert result.reversal_of_id == 40
    assert result.created_by_user_id == 7
    assert [line.line_no for line in result.lines] == [1, 2]
    assert [(line.debit, line.credit) for line in result.lines] == [
        (Decimal("0.00"), Decimal("55.00")),
        (Decimal("55.00"), Decimal("0.00")),
    ]
    assert [line.description for line in result.lines] == [
        "Reversal: debit line", "Reversal: JE-40",
    ]
    assert db.flush_calls == 1
    assert db.rollback_calls == 0
    assert db.commit_calls == 0


def test_repository_reverse_failure_rolls_back_and_recovers():
    db = RecordingSession(_original())
    repository = SqlAlchemyJournalRepository(db)
    db.fail_flush = True

    with pytest.raises(RuntimeError, match="reverse flush failed"):
        repository.reverse(_command("Custom reversal"))

    assert db.rollback_calls == 1
    assert db.added == []
    assert db.commit_calls == 0
    db.fail_flush = False
    recovered = repository.reverse(_command("Custom reversal"))
    assert recovered.description == "Custom reversal"
    assert db.commit_calls == 0


def test_repository_reverse_missing_original_is_internal_invariant_failure():
    db = RecordingSession()
    with pytest.raises(RuntimeError, match="disappeared before reversal"):
        SqlAlchemyJournalRepository(db).reverse(_command())
    assert db.flush_calls == 0
    assert db.commit_calls == 0