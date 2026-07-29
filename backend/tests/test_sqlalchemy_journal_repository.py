from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
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


class CountingSession(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commit_calls = 0

    def commit(self):
        self.commit_calls += 1
        return super().commit()


def test_sqlalchemy_journal_repository_preserves_read_contract():
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
        with CountingSession(engine) as db:
            first = Company(name="Journal Read First", base_currency="USD")
            second = Company(name="Journal Read Second", base_currency="USD")
            creator = User(
                email="journal-read@example.test",
                full_name="Journal Reader",
                hashed_password="not-used",
                is_active=True,
                is_superuser=False,
            )
            db.add_all([first, second, creator])
            db.flush()
            first_year = FiscalYear(
                company_id=first.id,
                name="FY 2026",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                status="open",
            )
            second_year = FiscalYear(
                company_id=second.id,
                name="FY 2026",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                status="open",
            )
            db.add_all([first_year, second_year])
            db.flush()
            first_period = FiscalPeriod(
                company_id=first.id,
                fiscal_year_id=first_year.id,
                period_no=1,
                name="January",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                status="open",
            )
            second_period = FiscalPeriod(
                company_id=second.id,
                fiscal_year_id=second_year.id,
                period_no=1,
                name="January",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                status="open",
            )
            account = Account(
                company_id=first.id,
                code="1000",
                name="Cash",
                account_type="asset",
                is_active=True,
                is_system=False,
            )
            db.add_all([first_period, second_period, account])
            db.flush()
            older = JournalEntry(
                company_id=first.id,
                fiscal_year_id=first_year.id,
                fiscal_period_id=first_period.id,
                entry_no="JE-OLD",
                entry_date=date(2026, 1, 1),
                status="draft",
            )
            newer = JournalEntry(
                company_id=first.id,
                fiscal_year_id=first_year.id,
                fiscal_period_id=first_period.id,
                entry_no="JE-NEW",
                entry_date=date(2026, 1, 2),
                status="posted",
                created_by_user_id=creator.id,
            )
            foreign = JournalEntry(
                company_id=second.id,
                fiscal_year_id=second_year.id,
                fiscal_period_id=second_period.id,
                entry_no="JE-FOREIGN",
                entry_date=date(2026, 1, 3),
                status="draft",
            )
            db.add_all([older, newer, foreign])
            db.flush()
            line = JournalLine(
                journal_entry_id=newer.id,
                company_id=first.id,
                account_id=account.id,
                line_no=1,
                debit=Decimal("10.00"),
                credit=Decimal("0.00"),
                description="Debit line",
            )
            db.add(line)
            db.commit()
            db.commit_calls = 0
            repository = SqlAlchemyJournalRepository(db)

            all_first = repository.list_by_company(first.id, None, 0, 10)
            posted = repository.list_by_company(first.id, "posted", 0, 10)
            page = repository.list_by_company(first.id, None, 1, 1)
            global_foreign = repository.get_by_id(foreign.id)

            assert [entry.entry_no for entry in all_first] == ["JE-NEW", "JE-OLD"]
            assert [entry.entry_no for entry in posted] == ["JE-NEW"]
            assert [entry.entry_no for entry in page] == ["JE-OLD"]
            assert repository.count_by_company(first.id, None) == 2
            assert repository.count_by_company(first.id, "draft") == 1
            assert global_foreign.company_id == second.id
            assert posted[0].creator_name == "Journal Reader"
            assert posted[0].lines[0].debit == Decimal("10.00")
            assert posted[0].lines[0].description == "Debit line"
            assert repository.get_by_id(999999) is None
            assert db.commit_calls == 0
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
