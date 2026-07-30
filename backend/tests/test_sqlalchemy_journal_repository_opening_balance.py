from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.application.journals.dto import (
    CreateJournalLineCommand,
    CreateOpeningBalanceCommand,
    JournalEntryDTO,
)
from app.infrastructure.database.sqlalchemy.repositories.journal_repository import (
    SqlAlchemyJournalRepository,
)


class RecordingSession:
    def __init__(self):
        self.added = []
        self.flush_calls = self.rollback_calls = self.commit_calls = 0
        self.fail_flush = False
        self.next_id = 200

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flush_calls += 1
        if self.fail_flush:
            raise RuntimeError("opening flush failed")
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


def _command():
    return CreateOpeningBalanceCommand(
        company_id=3, fiscal_year_id=4, fiscal_period_id=5,
        entry_no="OB-200", entry_date=date(2026, 1, 1),
        description="Opening balances", created_by_user_id=7,
        lines=(
            CreateJournalLineCommand(
                10, Decimal("60.00"), Decimal("0.00"), "debit"
            ),
            CreateJournalLineCommand(
                20, Decimal("0.00"), Decimal("60.00"), "credit"
            ),
        ),
    )


def test_repository_stages_opening_balance_lines_and_never_commits():
    db = RecordingSession()

    result = SqlAlchemyJournalRepository(db).create_opening_balance(_command())

    assert isinstance(result, JournalEntryDTO)
    assert result.company_id == 3
    assert result.entry_no == "OB-200"
    assert result.description == "Opening balances"
    assert result.status == "draft"
    assert result.source_type == "opening_balance"
    assert result.source_id is None
    assert result.created_by_user_id == 7
    assert [line.line_no for line in result.lines] == [1, 2]
    assert [(line.debit, line.credit) for line in result.lines] == [
        (Decimal("60.00"), Decimal("0.00")),
        (Decimal("0.00"), Decimal("60.00")),
    ]
    assert db.flush_calls == 1
    assert db.rollback_calls == 0
    assert db.commit_calls == 0


def test_repository_opening_balance_failure_rolls_back_and_recovers():
    db = RecordingSession()
    repository = SqlAlchemyJournalRepository(db)
    db.fail_flush = True

    with pytest.raises(RuntimeError, match="opening flush failed"):
        repository.create_opening_balance(_command())

    assert db.rollback_calls == 1
    assert db.added == []
    assert db.commit_calls == 0
    db.fail_flush = False
    assert repository.create_opening_balance(_command()).entry_no == "OB-200"
    assert db.commit_calls == 0