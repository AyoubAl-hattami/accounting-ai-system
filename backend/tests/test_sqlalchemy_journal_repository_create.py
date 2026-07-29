from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.journals.dto import (
    CreateJournalEntryCommand,
    CreateJournalLineCommand,
    JournalEntryDTO,
)
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


def _command(company_id, year_id, period_id, account_ids, entry_no):
    return CreateJournalEntryCommand(
        company_id=company_id,
        fiscal_year_id=year_id,
        fiscal_period_id=period_id,
        entry_no=entry_no,
        entry_date=date(2026, 1, 3),
        description=" journal description ",
        source_type="manual",
        source_id="source-3",
        created_by_user_id=None,
        lines=(
            CreateJournalLineCommand(
                account_id=account_ids[0],
                debit=Decimal("42.00"),
                credit=Decimal("0.00"),
                description="debit",
            ),
            CreateJournalLineCommand(
                account_id=account_ids[1],
                debit=Decimal("0.00"),
                credit=Decimal("42.00"),
                description="credit",
            ),
        ),
    )


def test_repository_stages_journal_lines_and_recovers_after_constraint_failure():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
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
    try:
        with RecordingSession(engine) as db:
            company = Company(name="Journal Create", base_currency="USD")
            db.add(company)
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
            period = FiscalPeriod(
                company_id=company.id,
                fiscal_year_id=year.id,
                period_no=1,
                name="January",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                status="open",
            )
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
            db.add_all([period, *accounts])
            db.commit()
            db.commit_calls = db.flush_calls = db.rollback_calls = 0
            repository = SqlAlchemyJournalRepository(db)
            command = _command(
                company.id,
                year.id,
                period.id,
                (accounts[0].id, accounts[1].id),
                "JE-CREATE-1",
            )

            result = repository.create(command)

            assert isinstance(result, JournalEntryDTO)
            assert result.entry_no == "JE-CREATE-1"
            assert result.status == "draft"
            assert result.description == " journal description "
            assert result.source_type == "manual"
            assert result.source_id == "source-3"
            assert [line.line_no for line in result.lines] == [1, 2]
            assert [line.account_id for line in result.lines] == [accounts[0].id, accounts[1].id]
            assert result.lines[0].debit == Decimal("42.00")
            assert result.lines[1].credit == Decimal("42.00")
            assert db.flush_calls >= 1
            assert db.commit_calls == 0
            db.commit()
            db.commit_calls = db.rollback_calls = 0

            with pytest.raises(IntegrityError):
                repository.create(command)

            assert db.rollback_calls == 1
            assert db.commit_calls == 0
            recovered = repository.create(
                _command(
                    company.id,
                    year.id,
                    period.id,
                    (accounts[0].id, accounts[1].id),
                    "JE-CREATE-2",
                )
            )
            assert recovered.entry_no == "JE-CREATE-2"
            assert db.commit_calls == 0
    finally:
        engine.dispose()
