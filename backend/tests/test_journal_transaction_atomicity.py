"""Focused transaction-boundary tests for journal mutations.

These tests use a recording session double to exercise transaction boundaries.
"""
from datetime import date
from types import SimpleNamespace

import pytest

from app.modules.accounting.models.audit_log import AuditLog
from app.modules.accounting.services import audit_service, journal_service


class RecordingSession:
    def __init__(self, existing=()):
        self.added = []
        self.commits = 0
        self.flushes = 0
        self.rollbacks = 0
        self._existing = list(existing)
        self._statuses = {id(item): item.status for item in existing if hasattr(item, "status")}
        self._next_id = 100

    def add(self, value):
        if value not in self.added:
            self.added.append(value)

    def flush(self):
        self.flushes += 1
        for value in self.added:
            if hasattr(value, "id") and value.id is None:
                value.id = self._next_id
                self._next_id += 1

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1
        for value in self._existing:
            if id(value) in self._statuses:
                value.status = self._statuses[id(value)]
        self.added = [value for value in self.added if value in self._existing]

    def get(self, _model, entity_id):
        return next((item for item in self._existing if getattr(item, "id", None) == entity_id), None)


def _entry(status="draft", *, entry_id=1, reversal_of_id=None):
    return SimpleNamespace(
        id=entry_id,
        company_id=7,
        fiscal_year_id=2,
        fiscal_period_id=3,
        entry_no=f"JE-{entry_id}",
        entry_date=date(2026, 7, 17),
        description="Atomic journal test",
        status=status,
        source_type="manual",
        source_id=None,
        reversal_of_id=reversal_of_id,
        posted_at=None,
        created_by_user_id=9,
        lines=[
            SimpleNamespace(account_id=10, debit=100, credit=0, description="Debit"),
            SimpleNamespace(account_id=11, debit=0, credit=100, description="Credit"),
        ],
    )


def _audit(db, entry, action):
    return audit_service.create_atomic_audit_log(
        db=db,
        company_id=entry.company_id,
        actor="actor@example.com",
        actor_user_id=9,
        actor_email="actor@example.com",
        actor_name="Actor",
        action=action,
        entity_type="journal_entry",
        entity_id=entry.id,
        description=action,
        old_values={"status": "before"},
        new_values={"status": entry.status},
    )


def _fail_audit(monkeypatch):
    def fail(**_kwargs):
        raise RuntimeError("audit insert failed")

    monkeypatch.setattr(audit_service, "create_audit_log", fail)


def test_journal_creation_rolls_back_when_audit_insert_fails(monkeypatch):
    db = RecordingSession()
    payload = SimpleNamespace(
        company_id=7,
        entry_no="JE-CREATE",
        entry_date=date(2026, 7, 17),
        description="Create",
        source_type="manual",
        source_id=None,
        lines=_entry().lines,
    )
    entry = journal_service.create_journal_entry(
        db, payload, SimpleNamespace(id=2), SimpleNamespace(id=3), 9
    )
    _fail_audit(monkeypatch)

    with pytest.raises(RuntimeError, match="audit insert failed"):
        _audit(db, entry, "create_journal_entry")

    assert db.commits == 0
    assert db.rollbacks == 1
    assert entry not in db.added


@pytest.mark.parametrize(
    ("initial_status", "mutate", "action"),
    [
        ("draft", journal_service.mark_journal_entry_reviewed, "review_journal_entry"),
        ("reviewed", journal_service.post_journal_entry, "post_journal_entry"),
        ("draft", journal_service.void_journal_entry, "void_journal_entry"),
    ],
)
def test_lifecycle_mutation_rolls_back_when_audit_insert_fails(
    monkeypatch, initial_status, mutate, action
):
    entry = _entry(initial_status)
    db = RecordingSession([entry])
    changed = mutate(db, entry)
    _fail_audit(monkeypatch)

    with pytest.raises(RuntimeError, match="audit insert failed"):
        _audit(db, changed, action)

    assert entry.status == initial_status
    assert db.commits == 0
    assert db.rollbacks == 1


def test_reversal_rolls_back_when_audit_insert_fails(monkeypatch):
    original = _entry("posted")
    db = RecordingSession([original])
    payload = SimpleNamespace(
        entry_no="REV-1", entry_date=date(2026, 7, 17), description="Reverse"
    )
    reversal = journal_service.reverse_journal_entry(
        db, original, payload, SimpleNamespace(id=2), SimpleNamespace(id=3), 9
    )
    _fail_audit(monkeypatch)

    with pytest.raises(RuntimeError, match="audit insert failed"):
        _audit(db, reversal, "reverse_journal_entry")

    assert db.commits == 0
    assert db.rollbacks == 1
    assert reversal not in db.added


def test_success_commits_mutation_and_exactly_one_audit_event_once():
    entry = _entry("draft")
    db = RecordingSession([entry])
    reviewed = journal_service.mark_journal_entry_reviewed(db, entry)

    audit = _audit(db, reviewed, "review_journal_entry")

    assert reviewed.status == "reviewed"
    assert db.commits == 1
    assert db.rollbacks == 0
    assert sum(isinstance(value, AuditLog) for value in db.added) == 1
    assert audit.action == "review_journal_entry"
    assert audit.entity_id == entry.id
    assert audit.company_id == entry.company_id
    assert audit.actor == "actor@example.com"
