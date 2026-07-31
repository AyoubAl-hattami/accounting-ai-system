"""Test-only factories for deterministic accounting data.

These helpers create explicit rows for tests that need database-backed API state.
They do not assume local seed data or stable primary key values.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.application.accounts.defaults import DEFAULT_ACCOUNTS
from app.core.security import hash_password
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.user import User
from app.modules.accounting.services.auth_service import create_user_token


DEFAULT_TEST_PASSWORD = "Password123"


@dataclass(frozen=True)
class AccountingBootstrap:
    user: User
    company: Company
    membership: CompanyUser
    fiscal_year: FiscalYear
    fiscal_period: FiscalPeriod
    accounts_by_code: dict[str, Account]

    @property
    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_user_token(self.user)}"}

    @property
    def company_id(self) -> int:
        return self.company.id

    def account_id(self, code: str) -> int:
        return self.accounts_by_code[code].id


class AccountingTestFactory:
    def __init__(self, db: Session):
        self.db = db

    def unique_email(self, prefix: str = "test-user") -> str:
        return f"{prefix}-{uuid4().hex}@example.test"

    def create_user(
        self,
        *,
        email: str | None = None,
        password: str = DEFAULT_TEST_PASSWORD,
        full_name: str = "Deterministic Test User",
        is_superuser: bool = False,
    ) -> User:
        user = User(
            email=email or self.unique_email(),
            full_name=full_name,
            hashed_password=hash_password(password),
            is_active=True,
            is_superuser=is_superuser,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def create_company(
        self,
        *,
        name: str | None = None,
        base_currency: str = "USD",
    ) -> Company:
        company = Company(
            name=name or f"Deterministic Company {uuid4().hex}",
            base_currency=base_currency,
            is_active=True,
        )
        self.db.add(company)
        self.db.flush()
        return company

    def add_company_user(
        self,
        *,
        company: Company,
        user: User,
        role: str = "admin",
    ) -> CompanyUser:
        membership = CompanyUser(
            company_id=company.id,
            user_id=user.id,
            role=role,
            is_active=True,
        )
        self.db.add(membership)
        self.db.flush()
        return membership

    def seed_default_accounts(self, *, company: Company) -> dict[str, Account]:
        accounts_by_code: dict[str, Account] = {}
        for definition in DEFAULT_ACCOUNTS:
            account = Account(
                company_id=company.id,
                code=definition.code,
                name=definition.name,
                account_type=definition.account_type,
                parent_id=None,
                description=definition.description,
                is_active=True,
                is_system=True,
            )
            self.db.add(account)
            accounts_by_code[account.code] = account

        self.db.flush()
        return accounts_by_code

    def create_open_fiscal_year(
        self,
        *,
        company: Company,
        year: int = 2026,
    ) -> FiscalYear:
        fiscal_year = FiscalYear(
            company_id=company.id,
            name=f"FY {year} {uuid4().hex[:8]}",
            start_date=date(year, 1, 1),
            end_date=date(year, 12, 31),
            status="open",
        )
        self.db.add(fiscal_year)
        self.db.flush()
        return fiscal_year

    def create_open_fiscal_period(
        self,
        *,
        company: Company,
        fiscal_year: FiscalYear,
        period_no: int = 1,
    ) -> FiscalPeriod:
        fiscal_period = FiscalPeriod(
            company_id=company.id,
            fiscal_year_id=fiscal_year.id,
            period_no=period_no,
            name=f"Period {period_no} {uuid4().hex[:8]}",
            start_date=date(fiscal_year.start_date.year, period_no, 1),
            end_date=date(fiscal_year.start_date.year, period_no, 28),
            status="open",
        )
        self.db.add(fiscal_period)
        self.db.flush()
        return fiscal_period

    def create_balanced_journal(
        self,
        *,
        bootstrap: AccountingBootstrap,
        debit_account_code: str = "1110",
        credit_account_code: str = "3100",
        amount: Decimal = Decimal("100.00"),
        status: str = "posted",
    ) -> JournalEntry:
        entry = JournalEntry(
            company_id=bootstrap.company.id,
            fiscal_year_id=bootstrap.fiscal_year.id,
            fiscal_period_id=bootstrap.fiscal_period.id,
            entry_no=f"JE-{uuid4().hex[:12]}",
            entry_date=bootstrap.fiscal_period.start_date,
            description="Deterministic balanced journal",
            status=status,
            created_by_user_id=bootstrap.user.id,
        )
        self.db.add(entry)
        self.db.flush()

        self.db.add_all(
            [
                JournalLine(
                    journal_entry_id=entry.id,
                    company_id=bootstrap.company.id,
                    account_id=bootstrap.account_id(debit_account_code),
                    line_no=1,
                    debit=amount,
                    credit=Decimal("0.00"),
                    description="Debit line",
                ),
                JournalLine(
                    journal_entry_id=entry.id,
                    company_id=bootstrap.company.id,
                    account_id=bootstrap.account_id(credit_account_code),
                    line_no=2,
                    debit=Decimal("0.00"),
                    credit=amount,
                    description="Credit line",
                ),
            ]
        )
        self.db.flush()
        return entry

    def create_accounting_bootstrap(
        self,
        *,
        role: str = "admin",
        include_journal: bool = False,
    ) -> AccountingBootstrap:
        user = self.create_user()
        company = self.create_company()
        membership = self.add_company_user(company=company, user=user, role=role)
        fiscal_year = self.create_open_fiscal_year(company=company)
        fiscal_period = self.create_open_fiscal_period(
            company=company,
            fiscal_year=fiscal_year,
        )
        accounts_by_code = self.seed_default_accounts(company=company)
        bootstrap = AccountingBootstrap(
            user=user,
            company=company,
            membership=membership,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            accounts_by_code=accounts_by_code,
        )
        if include_journal:
            self.create_balanced_journal(bootstrap=bootstrap)
        return bootstrap
