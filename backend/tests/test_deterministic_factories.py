from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.user import User
from factories.accounting import AccountingTestFactory


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


def test_accounting_bootstrap_uses_generated_ids_and_returns_auth_headers():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=FACTORY_TABLES)

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
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=FACTORY_TABLES)

    with Session(engine) as db:
        factory = AccountingTestFactory(db)
        bootstrap = factory.create_accounting_bootstrap(include_journal=True)
        db.commit()

        assert bootstrap.account_id("1110") != bootstrap.account_id("3100")
        assert len(bootstrap.accounts_by_code) == 13
