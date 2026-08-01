import calendar
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.clock import get_today_date
from app.core.database import Base
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.user import User
from factories.accounting import AccountingTestFactory, JournalLineSpec


FACTORY_TABLES = [
    User.__table__,
    Company.__table__,
    CompanyUser.__table__,
    FiscalYear.__table__,
    FiscalPeriod.__table__,
    Account.__table__,
    JournalEntry.__table__,
    JournalLine.__table__,
]


def _make_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=FACTORY_TABLES)
    return engine


def test_accounting_bootstrap_uses_generated_ids_and_returns_auth_headers():
    engine = _make_engine()

    with Session(engine) as db:
        factory = AccountingTestFactory(db)
        bootstrap = factory.create_accounting_bootstrap()
        db.commit()

        assert bootstrap.user.id is not None
        assert bootstrap.company.id is not None
        assert bootstrap.membership.company_id == bootstrap.company.id
        assert bootstrap.membership.user_id == bootstrap.user.id
        assert bootstrap.fiscal_year.company_id == bootstrap.company.id
        assert bootstrap.fiscal_period.fiscal_year_id == bootstrap.fiscal_year.id
        assert bootstrap.account_id("1110") is not None
        assert bootstrap.auth_headers["Authorization"].startswith("Bearer ")


def test_accounting_bootstrap_can_create_balanced_journal_data():
    engine = _make_engine()

    with Session(engine) as db:
        factory = AccountingTestFactory(db)
        bootstrap = factory.create_accounting_bootstrap(include_journal=True)
        db.commit()

        assert bootstrap.account_id("1110") != bootstrap.account_id("3100")
        assert len(bootstrap.accounts_by_code) == 13


def test_fiscal_year_defaults_to_current_year():
    """create_open_fiscal_year without an explicit year uses the production clock."""
    engine = _make_engine()

    with Session(engine) as db:
        factory = AccountingTestFactory(db)
        company = factory.create_company()
        fiscal_year = factory.create_open_fiscal_year(company=company)
        db.commit()

        today = get_today_date()
        assert fiscal_year.start_date.year == today.year
        assert fiscal_year.end_date.year == today.year


def test_fiscal_period_contains_today():
    """Default fiscal period covers the real current month, not a hardcoded month."""
    engine = _make_engine()

    with Session(engine) as db:
        factory = AccountingTestFactory(db)
        company = factory.create_company()
        fiscal_year = factory.create_open_fiscal_year(company=company)
        fiscal_period = factory.create_open_fiscal_period(
            company=company, fiscal_year=fiscal_year
        )
        db.commit()

        today = get_today_date()
        assert fiscal_period.start_date <= today <= fiscal_period.end_date


def test_fiscal_period_end_date_uses_correct_last_day():
    """end_date must be the true last day of the month (monthrange), not day 28."""
    engine = _make_engine()

    with Session(engine) as db:
        factory = AccountingTestFactory(db)
        company = factory.create_company()
        fiscal_year = factory.create_open_fiscal_year(company=company)
        fiscal_period = factory.create_open_fiscal_period(
            company=company, fiscal_year=fiscal_year
        )
        db.commit()

        year = fiscal_period.start_date.year
        month = fiscal_period.start_date.month
        _, expected_last_day = calendar.monthrange(year, month)
        assert fiscal_period.end_date == date(year, month, expected_last_day)


def test_default_accounts_parent_id_hierarchy():
    """seed_default_accounts wires parent_id correctly (two-pass seeding)."""
    engine = _make_engine()

    with Session(engine) as db:
        factory = AccountingTestFactory(db)
        company = factory.create_company()
        accounts = factory.seed_default_accounts(company=company)
        db.commit()

        # 1110 (Main Bank) must be a child of 1000 (Assets)
        assert accounts["1110"].parent_id == accounts["1000"].id

        # 4100 (Sales Revenue) must be a child of 4000 (Income)
        assert accounts["4100"].parent_id == accounts["4000"].id

        # Root accounts must have no parent
        for root_code in ("1000", "2000", "3000", "4000", "5000"):
            assert accounts[root_code].parent_id is None


def test_create_journal_generalised_interface():
    """create_journal accepts arbitrary line specs; create_balanced_journal is a wrapper."""
    engine = _make_engine()

    with Session(engine) as db:
        factory = AccountingTestFactory(db)
        bootstrap = factory.create_accounting_bootstrap()

        entry_date = bootstrap.fiscal_period.start_date
        amount = Decimal("250.00")
        entry = factory.create_journal(
            bootstrap=bootstrap,
            entry_date=entry_date,
            lines=[
                JournalLineSpec(
                    account_code="1110",
                    debit=amount,
                    credit=Decimal("0.00"),
                    description="Bank debit",
                ),
                JournalLineSpec(
                    account_code="4100",
                    debit=Decimal("0.00"),
                    credit=amount,
                    description="Revenue credit",
                ),
            ],
            description="Revenue journal",
            status="posted",
        )
        db.commit()

        assert entry.id is not None
        assert entry.entry_date == entry_date
        assert entry.description == "Revenue journal"
        assert entry.status == "posted"
        assert entry.company_id == bootstrap.company.id


def test_create_balanced_journal_backward_compatible():
    """create_balanced_journal still works after refactor to wrapper."""
    engine = _make_engine()

    with Session(engine) as db:
        factory = AccountingTestFactory(db)
        bootstrap = factory.create_accounting_bootstrap()
        entry = factory.create_balanced_journal(bootstrap=bootstrap)
        db.commit()

        assert entry.id is not None
        assert entry.status == "posted"
        assert entry.company_id == bootstrap.company.id
