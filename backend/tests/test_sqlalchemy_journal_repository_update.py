from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.journals.dto import UpdateJournalEntryCommand
from app.application.journals.use_cases import UpdateJournalEntry
from app.infrastructure.database.sqlalchemy.repositories.journal_repository import (
    SqlAlchemyJournalRepository,
)
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.user import User
from app.modules.accounting.services import audit_service


class RecordingSession(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commit_calls = 0
        self.flush_calls = 0
        self.rollback_calls = 0

    def commit(self):
        self.commit_calls += 1
        return super().commit()

    def flush(self, *args, **kwargs):
        self.flush_calls += 1
        return super().flush(*args, **kwargs)

    def rollback(self):
        self.rollback_calls += 1
        return super().rollback()


def _create_tables(engine):
    for table in (
        Company.__table__,
        User.__table__,
        FiscalYear.__table__,
        FiscalPeriod.__table__,
        Account.__table__,
        JournalEntry.__table__,
        JournalLine.__table__,
    ):
        table.create(engine)


def _seed(db):
    company = Company(name="Journal Update", base_currency="USD")
    creator = User(
        email="journal-update@example.test",
        full_name="Journal Updater",
        hashed_password="not-used",
        is_active=True,
        is_superuser=False,
    )
    db.add_all([company, creator])
    db.flush()
    year = FiscalYear(
        company_id=company.id,
        name="FY 2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="open",
    )
    db.add(year)
    db.flush()
    periods = [
        FiscalPeriod(
            company_id=company.id,
            fiscal_year_id=year.id,
            period_no=number,
            name=name,
            start_date=start,
            end_date=end,
            status="open",
        )
        for number, name, start, end in (
            (1, "January", date(2026, 1, 1), date(2026, 1, 31)),
            (2, "February", date(2026, 2, 1), date(2026, 2, 28)),
        )
    ]
    accounts = [
        Account(
            company_id=company.id,
            code=code,
            name=name,
            account_type=account_type,
            is_active=True,
            is_system=False,
        )
        for code, name, account_type in (
            ("1000", "Cash", "asset"),
            ("3000", "Capital", "equity"),
        )
    ]
    db.add_all([*periods, *accounts])
    db.flush()
    entry = JournalEntry(
        company_id=company.id,
        fiscal_year_id=year.id,
        fiscal_period_id=periods[0].id,
        entry_no="JE-UPDATE",
        entry_date=date(2026, 1, 3),
        description="Before",
        status="draft",
        source_type="manual",
        source_id="preserved",
        created_by_user_id=creator.id,
        lines=[
            JournalLine(
                company_id=company.id,
                account_id=accounts[0].id,
                line_no=1,
                debit=Decimal("12.00"),
                credit=Decimal("0.00"),
                description="debit",
            ),
            JournalLine(
                company_id=company.id,
                account_id=accounts[1].id,
                line_no=2,
                debit=Decimal("0.00"),
                credit=Decimal("12.00"),
                description="credit",
            ),
        ],
    )
    db.add(entry)
    db.commit()
    return company.id, year.id, periods[1].id, entry.id


def test_repository_updates_only_fields_preserves_lines_and_recovers_after_failure():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    _create_tables(engine)
    try:
        with RecordingSession(engine) as db:
            company_id, year_id, second_period_id, entry_id = _seed(db)
            db.commit_calls = db.flush_calls = db.rollback_calls = 0
            repository = SqlAlchemyJournalRepository(db)

            result = repository.update(
                UpdateJournalEntryCommand(
                    journal_entry_id=entry_id,
                    entry_date=date(2026, 2, 2),
                    description=None,
                    source_type=None,
                    source_id="not-supplied",
                    fiscal_year_id=year_id,
                    fiscal_period_id=second_period_id,
                    fields=frozenset(
                        {"entry_date", "description", "source_type"}
                    ),
                )
            )

            assert result.company_id == company_id
            assert result.entry_date == date(2026, 2, 2)
            assert result.description is None
            assert result.source_type is None
            assert result.source_id == "preserved"
            assert result.fiscal_year_id == year_id
            assert result.fiscal_period_id == second_period_id
            assert result.creator_name == "Journal Updater"
            assert [line.line_no for line in result.lines] == [1, 2]
            assert [line.debit for line in result.lines] == [
                Decimal("12.00"),
                Decimal("0.00"),
            ]
            assert db.flush_calls >= 1
            assert db.commit_calls == 0
            db.commit()
            db.commit_calls = db.rollback_calls = 0

            with pytest.raises(IntegrityError):
                repository.update(
                    UpdateJournalEntryCommand(
                        journal_entry_id=entry_id,
                        entry_date=None,
                        fields=frozenset({"entry_date"}),
                    )
                )

            assert db.rollback_calls == 1
            assert db.commit_calls == 0
            recovered = repository.update(
                UpdateJournalEntryCommand(
                    journal_entry_id=entry_id,
                    source_id="recovered",
                    fields=frozenset({"source_id"}),
                )
            )
            assert recovered.source_id == "recovered"
            assert db.commit_calls == 0
    finally:
        engine.dispose()


def test_audit_failure_rolls_back_staged_journal_update(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    _create_tables(engine)
    try:
        with Session(engine) as db:
            company_id, _year_id, _period_id, entry_id = _seed(db)
            updated = UpdateJournalEntry(
                SqlAlchemyJournalRepository(db)
            ).execute(
                UpdateJournalEntryCommand(
                    journal_entry_id=entry_id,
                    description="After",
                    fields=frozenset({"description"}),
                )
            )
            assert updated.description == "After"

            def fail(**_kwargs):
                raise RuntimeError("audit insert failed")

            monkeypatch.setattr(audit_service, "create_audit_log", fail)
            with pytest.raises(RuntimeError, match="audit insert failed"):
                audit_service.create_atomic_audit_log(
                    db=db,
                    company_id=company_id,
                    action="update_journal_entry",
                    entity_type="journal_entry",
                    entity_id=entry_id,
                )

        with Session(engine) as verification_db:
            assert verification_db.get(JournalEntry, entry_id).description == "Before"
    finally:
        engine.dispose()