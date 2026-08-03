"""Test-only factories for deterministic accounting data.

These helpers create explicit rows for tests that need database-backed API state.
They do not assume local seed data or stable primary key values.
"""

from __future__ import annotations

import calendar
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.accounts.defaults import DEFAULT_ACCOUNTS
from app.core.clock import get_today_date
from app.core.security import hash_password
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.assistant_conversation import AssistantConversation
from app.modules.accounting.models.audit_log import AuditLog
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_subscription import CompanySubscription
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.company_user_invitation import CompanyUserInvitation
from app.modules.accounting.models.fiscal_period import FiscalPeriod
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine
from app.modules.accounting.models.user import User
from app.modules.accounting.services.auth_service import create_user_token


DEFAULT_TEST_PASSWORD = "Password123"


@dataclass(frozen=True)
class JournalLineSpec:
    """Specification for a single journal line used by create_journal."""

    account_code: str
    debit: Decimal
    credit: Decimal
    description: str = ""


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

    # ── identity helpers ──────────────────────────────────────────────────────

    def unique_email(self, prefix: str = "test-user") -> str:
        return f"{prefix}-{uuid4().hex}@accounting-ai-test.dev"

    def auth_headers_for(self, user: User) -> dict[str, str]:
        """Return Bearer auth headers for the given user."""
        return {"Authorization": f"Bearer {create_user_token(user)}"}

    # ── user / company creation ───────────────────────────────────────────────

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

    def create_superuser(self, *, email: str | None = None) -> User:
        """Create a platform superuser."""
        return self.create_user(email=email, is_superuser=True)

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

    def set_subscription(
        self,
        *,
        company: Company,
        status: str = "active",
        expires_at: datetime | None = None,
        plan_code: str | None = None,
        suspension_reason: str | None = None,
    ) -> CompanySubscription:
        """Create or overwrite the company's single subscription record."""
        subscription = self.db.scalar(
            select(CompanySubscription).where(
                CompanySubscription.company_id == company.id
            )
        )
        if subscription is None:
            subscription = CompanySubscription(company_id=company.id)
            self.db.add(subscription)

        subscription.status = status
        subscription.expires_at = expires_at
        subscription.plan_code = plan_code
        subscription.suspension_reason = suspension_reason
        self.db.flush()
        return subscription

    def add_member(
        self,
        *,
        company: Company,
        role: str = "viewer",
        full_name: str | None = None,
    ) -> tuple[User, CompanyUser]:
        """Create a new user and add them to the company with the given role."""
        user = self.create_user(
            full_name=full_name or f"Member {uuid4().hex[:6]}",
        )
        membership = self.add_company_user(company=company, user=user, role=role)
        return user, membership

    # ── accounts ──────────────────────────────────────────────────────────────

    def seed_default_accounts(self, *, company: Company) -> dict[str, Account]:
        """Create default chart-of-accounts and wire parent_id hierarchy.

        Two passes are required: pass 1 creates all accounts (so every ORM
        object has an id after flush); pass 2 sets parent_id using the
        parent_code recorded in DEFAULT_ACCOUNTS.
        """
        accounts_by_code: dict[str, Account] = {}

        # Pass 1 — create all accounts with parent_id=None
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

        # Pass 2 — wire parent_id from parent_code
        for definition in DEFAULT_ACCOUNTS:
            if definition.parent_code is not None:
                child = accounts_by_code[definition.code]
                parent = accounts_by_code[definition.parent_code]
                child.parent_id = parent.id

        self.db.flush()
        return accounts_by_code

    # ── fiscal year / period ──────────────────────────────────────────────────

    def create_open_fiscal_year(
        self,
        *,
        company: Company,
        year: int | None = None,
    ) -> FiscalYear:
        """Create an open fiscal year defaulting to the current calendar year."""
        if year is None:
            year = get_today_date().year
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
        period_no: int | None = None,
    ) -> FiscalPeriod:
        """Create an open fiscal period for the given month number.

        Defaults to the current month so the period always contains today.
        end_date uses calendar.monthrange to handle months shorter than 31 days
        and February in leap years correctly.
        """
        year = fiscal_year.start_date.year
        if period_no is None:
            period_no = get_today_date().month
        _, last_day = calendar.monthrange(year, period_no)
        fiscal_period = FiscalPeriod(
            company_id=company.id,
            fiscal_year_id=fiscal_year.id,
            period_no=period_no,
            name=f"Period {period_no} {uuid4().hex[:8]}",
            start_date=date(year, period_no, 1),
            end_date=date(year, period_no, last_day),
            status="open",
        )
        self.db.add(fiscal_period)
        self.db.flush()
        return fiscal_period

    # ── journal entries ───────────────────────────────────────────────────────

    def create_journal(
        self,
        *,
        bootstrap: AccountingBootstrap,
        lines: Sequence[JournalLineSpec],
        entry_date: date | None = None,
        description: str = "Deterministic journal",
        status: str = "posted",
    ) -> JournalEntry:
        """Create a journal entry with arbitrary lines.

        Lines must balance (sum of debits == sum of credits); the caller is
        responsible for ensuring balance.  entry_date defaults to the fiscal
        period start date.
        """
        if entry_date is None:
            entry_date = bootstrap.fiscal_period.start_date
        entry = JournalEntry(
            company_id=bootstrap.company.id,
            fiscal_year_id=bootstrap.fiscal_year.id,
            fiscal_period_id=bootstrap.fiscal_period.id,
            entry_no=f"JE-{uuid4().hex[:12]}",
            entry_date=entry_date,
            description=description,
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
                    account_id=bootstrap.account_id(spec.account_code),
                    line_no=idx + 1,
                    debit=spec.debit,
                    credit=spec.credit,
                    description=spec.description,
                )
                for idx, spec in enumerate(lines)
            ]
        )
        self.db.flush()
        return entry

    def create_balanced_journal(
        self,
        *,
        bootstrap: AccountingBootstrap,
        debit_account_code: str = "1110",
        credit_account_code: str = "3100",
        amount: Decimal = Decimal("100.00"),
        status: str = "posted",
    ) -> JournalEntry:
        """Backward-compatible wrapper around create_journal.

        Creates a simple two-line balanced entry: one debit and one credit of
        equal amount.
        """
        return self.create_journal(
            bootstrap=bootstrap,
            lines=[
                JournalLineSpec(
                    account_code=debit_account_code,
                    debit=amount,
                    credit=Decimal("0.00"),
                    description="Debit line",
                ),
                JournalLineSpec(
                    account_code=credit_account_code,
                    debit=Decimal("0.00"),
                    credit=amount,
                    description="Credit line",
                ),
            ],
            description="Deterministic balanced journal",
            status=status,
        )

    def create_profit_and_loss_data(
        self,
        *,
        bootstrap: AccountingBootstrap,
        revenue_amount: Decimal = Decimal("2000.00"),
        expense_amount: Decimal = Decimal("500.00"),
    ) -> tuple[JournalEntry, JournalEntry]:
        """Create posted revenue and expense journal entries for P&L tests."""
        revenue = self.create_journal(
            bootstrap=bootstrap,
            lines=[
                JournalLineSpec("1110", revenue_amount, Decimal("0.00"), "Bank debit"),
                JournalLineSpec(
                    "4100", Decimal("0.00"), revenue_amount, "Sales revenue credit"
                ),
            ],
            description="Revenue entry",
            status="posted",
        )
        expense = self.create_journal(
            bootstrap=bootstrap,
            lines=[
                JournalLineSpec(
                    "5100", expense_amount, Decimal("0.00"), "Rent expense debit"
                ),
                JournalLineSpec("1110", Decimal("0.00"), expense_amount, "Bank credit"),
            ],
            description="Expense entry",
            status="posted",
        )
        return revenue, expense

    # ── invitations ───────────────────────────────────────────────────────────

    def create_invitation(
        self,
        *,
        company: Company,
        invited_by: User,
        email: str | None = None,
        role: str = "viewer",
        expires_days: int = 7,
    ) -> tuple[CompanyUserInvitation, str]:
        """Create an invitation and return (invite, full_token).

        full_token mirrors the format f'{invite.id}:{raw_token}' produced by
        the invitation service so tests can accept or verify invitations.
        """
        raw_token = secrets.token_urlsafe(32)
        invite_email = email or self.unique_email(prefix="invited-user")
        normalized = invite_email.lower().strip()
        invite = CompanyUserInvitation(
            company_id=company.id,
            email=invite_email,
            normalized_email=normalized,
            role=role,
            token_hash=hash_password(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days),
            invited_by_user_id=invited_by.id,
        )
        self.db.add(invite)
        self.db.flush()
        return invite, f"{invite.id}:{raw_token}"

    # ── assistant conversations ───────────────────────────────────────────────

    def create_assistant_conversation(
        self,
        *,
        company: Company,
        user: User,
        title: str = "Test Conversation",
        title_source: str = "fallback",
        status: str = "active",
    ) -> AssistantConversation:
        """Create an assistant conversation for the given company and user."""
        conv = AssistantConversation(
            company_id=company.id,
            user_id=user.id,
            title=title,
            title_source=title_source,
            status=status,
        )
        self.db.add(conv)
        self.db.flush()
        return conv

    # ── multi-year bootstrap ──────────────────────────────────────────────────

    def create_multi_year_bootstrap(
        self,
        *,
        role: str = "admin",
        prior_years: int = 1,
    ) -> AccountingBootstrap:
        """Create a bootstrap that spans multiple fiscal years.

        Returns the current-year bootstrap.  Prior fiscal years (prior_years
        prior to the current year) are created on the same company with the
        same accounts so cross-year reports work.
        """
        bootstrap = self.create_accounting_bootstrap(role=role)
        current_year = get_today_date().year
        for offset in range(prior_years, 0, -1):
            self.create_open_fiscal_year(
                company=bootstrap.company, year=current_year - offset
            )
        return bootstrap

    # ── audit log assertions ──────────────────────────────────────────────────

    def assert_audit_log(
        self,
        *,
        company: Company,
        action: str,
        entity_type: str,
        entity_id: int | None = None,
    ) -> AuditLog:
        """Assert and return an audit log entry scoped to the factory company."""
        q = (
            select(AuditLog)
            .where(AuditLog.company_id == company.id)
            .where(AuditLog.action == action)
            .where(AuditLog.entity_type == entity_type)
        )
        if entity_id is not None:
            q = q.where(AuditLog.entity_id == entity_id)
        log = self.db.scalar(q)
        assert log is not None, (
            f"No audit log found: action={action!r}, entity_type={entity_type!r}, "
            f"company_id={company.id}"
        )
        return log

    # ── full bootstrap ────────────────────────────────────────────────────────

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
