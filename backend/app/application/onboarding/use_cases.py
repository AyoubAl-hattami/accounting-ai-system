"""Client onboarding orchestration.

One call stands up a whole tenant: company, first admin, membership,
subscription, and optionally the default chart of accounts and a fiscal
calendar.  The use case composes the existing per-domain use cases rather than
reaching past them, so every invariant those already enforce still applies.

Two rules shape the design:

* The platform owner is never a member of the company it creates.  Nothing here
  takes the acting admin's user id — the only membership written is the client
  admin's.
* Transaction ownership stays at the route boundary.  Repositories flush, this
  use case never commits, so a failure anywhere leaves the caller free to roll
  the whole onboarding back.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime

from app.application.accounts.defaults import DEFAULT_ACCOUNTS
from app.application.accounts.dto import SeedDefaultAccountsCommand
from app.application.accounts.ports import AccountRepository
from app.application.accounts.use_cases import SeedDefaultAccounts
from app.application.companies.dto import CreateCompanyCommand
from app.application.companies.ports import CompanyRepository
from app.application.companies.use_cases import CreateCompany
from app.application.company_users.dto import CreateCompanyUserCommand
from app.application.company_users.ports import CompanyUserRepository
from app.application.company_users.use_cases import CreateCompanyUser
from app.application.fiscal.dto import (
    CreateFiscalPeriodCommand,
    CreateFiscalYearCommand,
)
from app.application.fiscal.ports import FiscalRepository
from app.application.fiscal.use_cases import (
    CreateFiscalPeriod,
    CreateFiscalYear,
    FindFiscalPeriodForDate,
    FindFiscalYearForDate,
)
from app.application.onboarding.dto import OnboardClientCommand, OnboardedClientDTO
from app.application.onboarding.errors import (
    AdminEmailTaken,
    CompanyNameTaken,
    InvalidSubscriptionWindow,
    MissingTemporaryPassword,
    ReusedAdminIsInactive,
    ReusedAdminIsPlatformAdmin,
)
from app.application.subscriptions.dto import UpdateSubscriptionCommand
from app.application.subscriptions.policy import (
    GRANTING_STATUSES,
    STATUS_TRIAL,
    days_remaining,
    effective_status,
    utc_now,
)
from app.application.subscriptions.ports import SubscriptionRepository
from app.application.users.dto import CreateUserCommand
from app.application.users.ports import UserRepository
from app.application.users.use_cases import CreateUser


# Spelled out rather than taken from ``calendar.month_name``, which follows the
# process locale and would give a client a differently-named ledger depending on
# which machine onboarded them.
MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

ADMIN_ROLE = "admin"
FISCAL_OPEN = "open"


def _normalize_email(email: str) -> str:
    """Mirror ``app.core.identity.normalize_email`` without importing it.

    The application layer stays framework- and adapter-neutral, so the one-line
    rule is restated here; the user repository applies the same normalisation
    when it looks an account up.
    """
    return email.strip().lower()


def _monthly_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


class OnboardClient:
    """Create one client tenant end to end."""

    def __init__(
        self,
        *,
        companies: CompanyRepository,
        users: UserRepository,
        company_users: CompanyUserRepository,
        subscriptions: SubscriptionRepository,
        accounts: AccountRepository,
        fiscal: FiscalRepository,
    ) -> None:
        self._companies = companies
        self._users = users
        self._company_users = company_users
        self._subscriptions = subscriptions
        self._accounts = accounts
        self._fiscal = fiscal

    def execute(
        self,
        command: OnboardClientCommand,
        *,
        now: datetime | None = None,
    ) -> OnboardedClientDTO:
        moment = now or utc_now()

        company_name = command.company_name.strip()
        admin_email = _normalize_email(command.admin_email)
        expires_at, trial_ends_at = self._resolve_window(command, moment)

        # Every refusal is raised before the first write, so a rejected
        # onboarding never leaves a half-created tenant behind even if the
        # caller forgets to roll back.
        if self._companies.find_by_name(company_name) is not None:
            raise CompanyNameTaken(company_name)

        existing_admin = self._users.get_by_email(admin_email)
        if existing_admin is not None:
            if not command.reuse_existing_user:
                raise AdminEmailTaken(admin_email)
            if existing_admin.is_superuser:
                raise ReusedAdminIsPlatformAdmin(admin_email)
            if not existing_admin.is_active:
                raise ReusedAdminIsInactive(admin_email)
        elif not command.temporary_password:
            raise MissingTemporaryPassword(admin_email)

        company = CreateCompany(self._companies).execute(
            CreateCompanyCommand(
                name=company_name,
                base_currency=command.base_currency,
            )
        )

        if existing_admin is None:
            admin = CreateUser(self._users).execute(
                CreateUserCommand(
                    email=admin_email,
                    password=command.temporary_password,
                    full_name=command.admin_full_name,
                )
            )
        else:
            admin = existing_admin

        # The only membership written by onboarding.  The acting platform admin
        # is never added.
        CreateCompanyUser(self._company_users).execute(
            CreateCompanyUserCommand(
                company_id=company.id,
                user_id=admin.id,
                role=ADMIN_ROLE,
                is_active=True,
            )
        )

        subscription = self._open_subscription(
            company_id=company.id,
            status=command.subscription_status,
            plan_code=command.plan_code,
            expires_at=expires_at,
            trial_ends_at=trial_ends_at,
        )

        seeded_accounts = 0
        if command.seed_default_accounts:
            seeded_accounts = (
                SeedDefaultAccounts(self._accounts)
                .execute(
                    SeedDefaultAccountsCommand(
                        company_id=company.id,
                        accounts=DEFAULT_ACCOUNTS,
                    )
                )
                .created_count
            )

        fiscal_year_created = False
        periods_created = 0
        if command.create_fiscal_year:
            fiscal_year_created, periods_created = self._open_fiscal_calendar(
                company_id=company.id,
                year=moment.year,
                open_monthly_periods=command.open_monthly_periods,
            )

        return OnboardedClientDTO(
            company_id=company.id,
            company_name=company.name,
            base_currency=company.base_currency,
            admin_user_id=admin.id,
            admin_email=admin.email,
            admin_was_existing=existing_admin is not None,
            subscription_status=subscription.status,
            effective_status=effective_status(
                subscription.status, subscription.expires_at, moment
            ),
            plan_code=subscription.plan_code,
            expires_at=subscription.expires_at,
            trial_ends_at=subscription.trial_ends_at,
            days_remaining=days_remaining(subscription.expires_at, moment),
            seeded_accounts_count=seeded_accounts,
            fiscal_year_created=fiscal_year_created,
            fiscal_periods_created=periods_created,
        )

    # ── internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_window(
        command: OnboardClientCommand,
        moment: datetime,
    ) -> tuple[datetime | None, datetime | None]:
        """Decide the expiry the access gate will actually read.

        ``effective_status`` only ever looks at ``expires_at``, so a trial that
        carried nothing but ``trial_ends_at`` would never lapse.  For a trial the
        trial end therefore doubles as the expiry unless one was given
        explicitly.
        """
        expires_at = command.subscription_expires_at
        trial_ends_at = command.trial_ends_at

        if command.subscription_status == STATUS_TRIAL and expires_at is None:
            expires_at = trial_ends_at

        if (
            command.subscription_status in GRANTING_STATUSES
            and expires_at is not None
            and expires_at <= moment
        ):
            raise InvalidSubscriptionWindow(str(expires_at))

        return expires_at, trial_ends_at

    def _open_subscription(
        self,
        *,
        company_id: int,
        status: str,
        plan_code: str | None,
        expires_at: datetime | None,
        trial_ends_at: datetime | None,
    ):
        self._subscriptions.get_or_create(company_id)
        return self._subscriptions.update(
            UpdateSubscriptionCommand(
                company_id=company_id,
                fields=frozenset(
                    {
                        "status",
                        "plan_code",
                        "expires_at",
                        "trial_ends_at",
                        "suspended_at",
                        "cancelled_at",
                        "suspension_reason",
                    }
                ),
                status=status,
                plan_code=plan_code,
                expires_at=expires_at,
                trial_ends_at=trial_ends_at,
                suspended_at=None,
                cancelled_at=None,
                suspension_reason=None,
            )
        )

    def _open_fiscal_calendar(
        self,
        *,
        company_id: int,
        year: int,
        open_monthly_periods: bool,
    ) -> tuple[bool, int]:
        """Create the calendar year and its twelve open months, idempotently.

        The company is brand new, so nothing should exist yet — but the lookups
        are kept so a re-run (or a company created another way) can never
        produce overlapping years or duplicate periods.
        """
        year_start = date(year, 1, 1)
        fiscal_year = FindFiscalYearForDate(self._fiscal).execute(company_id, year_start)
        created = False

        if fiscal_year is None:
            fiscal_year = CreateFiscalYear(self._fiscal).execute(
                CreateFiscalYearCommand(
                    company_id=company_id,
                    name=str(year),
                    start_date=year_start,
                    end_date=date(year, 12, 31),
                    status=FISCAL_OPEN,
                )
            )
            created = True

        if not open_monthly_periods:
            return created, 0

        periods_created = 0
        for period_no in range(1, 13):
            period_start, period_end = _monthly_bounds(year, period_no)
            if (
                FindFiscalPeriodForDate(self._fiscal).execute(company_id, period_start)
                is not None
            ):
                continue
            CreateFiscalPeriod(self._fiscal).execute(
                CreateFiscalPeriodCommand(
                    company_id=company_id,
                    fiscal_year_id=fiscal_year.id,
                    period_no=period_no,
                    name=f"{MONTH_NAMES[period_no - 1]} {year}",
                    start_date=period_start,
                    end_date=period_end,
                    status=FISCAL_OPEN,
                )
            )
            periods_created += 1

        return created, periods_created
