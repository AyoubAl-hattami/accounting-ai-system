"""
Local demo seed data for the accounting system.

Creates a demo admin user, a demo company, the default chart of accounts, an
open fiscal year with twelve open monthly periods, and a small set of posted
journal entries so every report shows real numbers.

The script is idempotent: existing rows are detected and left untouched, so it
can be re-run safely. It refuses to run when APP_ENV is "production".

Demo credentials are for local development only. Never seed a production
database with this script.

Usage:
    cd C:\\ayoub\\accounting-ai-system\\backend
    .venv\\Scripts\\activate
    $env:PYTHONPATH = "C:\\ayoub\\accounting-ai-system\\backend"
    python scripts/seed_demo_data.py

    # Also reset the demo user's password back to the documented value:
    python scripts/seed_demo_data.py --reset-demo-password
"""

from __future__ import annotations

import argparse
import calendar
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.application.accounts.defaults import DEFAULT_ACCOUNTS
from app.application.accounts.dto import SeedDefaultAccountsCommand
from app.application.accounts.use_cases import ListAccounts, SeedDefaultAccounts
from app.application.companies.dto import CreateCompanyCommand
from app.application.companies.use_cases import CreateCompany, GetCompany
from app.application.company_users.dto import CreateCompanyUserCommand
from app.application.company_users.use_cases import (
    CreateCompanyUser,
    GetCompanyUserByCompanyAndUser,
)
from app.application.fiscal.dto import (
    CreateFiscalPeriodCommand,
    CreateFiscalYearCommand,
)
from app.application.fiscal.use_cases import (
    CreateFiscalPeriod,
    CreateFiscalYear,
    FindFiscalPeriodForDate,
    FindFiscalYearForDate,
)
from app.application.journals.dto import (
    CreateJournalEntryCommand,
    CreateJournalLineCommand,
    CreateOpeningBalanceCommand,
    PostJournalEntryCommand,
    ReviewJournalEntryCommand,
)
from app.application.journals.use_cases import (
    CreateJournalEntry,
    CreateOpeningBalance,
    GetJournalEntryByNo,
    PostJournalEntry,
    ReviewJournalEntry,
)
from app.application.users.dto import CreateUserCommand
from app.application.users.use_cases import CreateUser, LookupUserByEmail
from app.core.clock import get_today_date
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.infrastructure.database.sqlalchemy.repositories.account_repository import (
    SqlAlchemyAccountRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.company_repository import (
    SqlAlchemyCompanyRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.company_user_repository import (
    SqlAlchemyCompanyUserRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.fiscal_repository import (
    SqlAlchemyFiscalRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.journal_repository import (
    SqlAlchemyJournalRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.user import User


DEMO_ADMIN_EMAIL = "admin@example.com"
DEMO_ADMIN_PASSWORD = "Password123"
DEMO_ADMIN_FULL_NAME = "Demo Admin"
DEMO_ADMIN_ROLE = "admin"

DEMO_COMPANY_NAME = "Demo Company Ltd"
DEMO_COMPANY_CURRENCY = "USD"
DEMO_COMPANY_LEGAL_NAME = "Demo Company Limited"

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


@dataclass(frozen=True)
class DemoLineSpec:
    account_code: str
    debit: Decimal
    credit: Decimal
    description: str


@dataclass(frozen=True)
class DemoEntrySpec:
    entry_no: str
    entry_date: date
    description: str
    is_opening_balance: bool
    lines: tuple[DemoLineSpec, ...]

    @property
    def total_debit(self) -> Decimal:
        return sum((line.debit for line in self.lines), Decimal("0.00"))

    @property
    def total_credit(self) -> Decimal:
        return sum((line.credit for line in self.lines), Decimal("0.00"))

    @property
    def is_balanced(self) -> bool:
        return self.total_debit > 0 and self.total_debit == self.total_credit


# ── pure planning helpers (unit-testable without a database) ──────────────────


def shift_month(month_start: date, months: int) -> date:
    """Return the first day of the month `months` away from `month_start`."""
    total = (month_start.year * 12 + month_start.month - 1) + months
    return date(total // 12, total % 12 + 1, 1)


def fiscal_year_bounds(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year, 12, 31)


def monthly_period_bounds(year: int, period_no: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, period_no)[1]
    return date(year, period_no, 1), date(year, period_no, last_day)


def clamp_entry_date(
    month_start: date,
    day: int,
    year_start: date,
    today: date,
) -> date:
    """Pin a demo entry to a real date inside the fiscal year and not in the future."""
    last_day = calendar.monthrange(month_start.year, month_start.month)[1]
    candidate = month_start.replace(day=min(day, last_day))
    if candidate < year_start:
        candidate = year_start
    if candidate > today:
        candidate = today
    return candidate


def build_demo_entries(today: date) -> tuple[DemoEntrySpec, ...]:
    """Build the demo journal plan relative to `today`.

    Entries are spread over the current month and the two preceding months so
    period-scoped reports have data, and clamped into the current fiscal year.
    """
    year_start, _ = fiscal_year_bounds(today.year)
    this_month = date(today.year, today.month, 1)
    prev_month = shift_month(this_month, -1)
    two_months_ago = shift_month(this_month, -2)

    def at(month_start: date, day: int) -> date:
        return clamp_entry_date(month_start, day, year_start, today)

    specs = (
        DemoEntrySpec(
            entry_no="DEMO-OB-0001",
            entry_date=year_start,
            description="Opening balances",
            is_opening_balance=True,
            lines=(
                DemoLineSpec("1110", Decimal("50000.00"), Decimal("0.00"), "Opening bank balance"),
                DemoLineSpec("3100", Decimal("0.00"), Decimal("50000.00"), "Owner capital introduced"),
            ),
        ),
        DemoEntrySpec(
            entry_no="DEMO-JE-0001",
            entry_date=at(two_months_ago, 5),
            description="Cash sales received in bank",
            is_opening_balance=False,
            lines=(
                DemoLineSpec("1110", Decimal("18500.00"), Decimal("0.00"), "Sales proceeds banked"),
                DemoLineSpec("4100", Decimal("0.00"), Decimal("18500.00"), "Sales revenue"),
            ),
        ),
        DemoEntrySpec(
            entry_no="DEMO-JE-0002",
            entry_date=at(two_months_ago, 12),
            description="Office rent paid",
            is_opening_balance=False,
            lines=(
                DemoLineSpec("5100", Decimal("2400.00"), Decimal("0.00"), "Monthly office rent"),
                DemoLineSpec("1110", Decimal("0.00"), Decimal("2400.00"), "Rent paid from bank"),
            ),
        ),
        DemoEntrySpec(
            entry_no="DEMO-JE-0003",
            entry_date=at(prev_month, 6),
            description="Office software and supplies purchased on account",
            is_opening_balance=False,
            lines=(
                DemoLineSpec("5200", Decimal("1250.00"), Decimal("0.00"), "Software subscriptions and office supplies"),
                DemoLineSpec("2100", Decimal("0.00"), Decimal("1250.00"), "Supplier invoice payable"),
            ),
        ),
        DemoEntrySpec(
            entry_no="DEMO-JE-0004",
            entry_date=at(prev_month, 18),
            description="Service income invoiced on credit",
            is_opening_balance=False,
            lines=(
                DemoLineSpec("1200", Decimal("9750.00"), Decimal("0.00"), "Customer invoice raised"),
                DemoLineSpec("4100", Decimal("0.00"), Decimal("9750.00"), "Service income"),
            ),
        ),
        DemoEntrySpec(
            entry_no="DEMO-JE-0005",
            entry_date=at(this_month, 4),
            description="Customer settled part of outstanding invoices",
            is_opening_balance=False,
            lines=(
                DemoLineSpec("1110", Decimal("6250.00"), Decimal("0.00"), "Customer payment received"),
                DemoLineSpec("1200", Decimal("0.00"), Decimal("6250.00"), "Receivable cleared"),
            ),
        ),
        DemoEntrySpec(
            entry_no="DEMO-JE-0006",
            entry_date=at(this_month, 8),
            description="Part payment of supplier invoice",
            is_opening_balance=False,
            lines=(
                DemoLineSpec("2100", Decimal("500.00"), Decimal("0.00"), "Supplier payable settled"),
                DemoLineSpec("1110", Decimal("0.00"), Decimal("500.00"), "Payment from bank"),
            ),
        ),
        DemoEntrySpec(
            entry_no="DEMO-JE-0007",
            entry_date=at(this_month, 10),
            description="Office rent paid",
            is_opening_balance=False,
            lines=(
                DemoLineSpec("5100", Decimal("2400.00"), Decimal("0.00"), "Monthly office rent"),
                DemoLineSpec("1110", Decimal("0.00"), Decimal("2400.00"), "Rent paid from bank"),
            ),
        ),
    )

    unbalanced = [spec.entry_no for spec in specs if not spec.is_balanced]
    if unbalanced:
        raise ValueError(f"Demo journal plan is not balanced: {', '.join(unbalanced)}")

    return specs


def is_production_environment() -> bool:
    return settings.APP_ENV.strip().lower() == "production"


# ── seeding ───────────────────────────────────────────────────────────────────


def _log(message: str) -> None:
    print(f"  {message}")


def seed_demo_data(*, reset_demo_password: bool = False) -> dict[str, int]:
    """Seed demo data and return a summary of what was created versus reused."""
    today = get_today_date()
    year_start, year_end = fiscal_year_bounds(today.year)
    entry_specs = build_demo_entries(today)

    summary = {
        "users_created": 0,
        "companies_created": 0,
        "memberships_created": 0,
        "accounts_created": 0,
        "accounts_existing": 0,
        "fiscal_years_created": 0,
        "fiscal_periods_created": 0,
        "journal_entries_created": 0,
        "journal_entries_existing": 0,
    }

    db = SessionLocal()
    try:
        user_repository = SqlAlchemyUserRepository(db)
        company_repository = SqlAlchemyCompanyRepository(db)
        company_user_repository = SqlAlchemyCompanyUserRepository(db)
        account_repository = SqlAlchemyAccountRepository(db)
        fiscal_repository = SqlAlchemyFiscalRepository(db)
        journal_repository = SqlAlchemyJournalRepository(db)

        print("\n" + "=" * 64)
        print("  Seeding local demo data")
        print("=" * 64 + "\n")

        # 1. Demo admin user
        user = LookupUserByEmail(user_repository).execute(DEMO_ADMIN_EMAIL)
        if user is None:
            user = CreateUser(user_repository).execute(
                CreateUserCommand(
                    email=DEMO_ADMIN_EMAIL,
                    password=DEMO_ADMIN_PASSWORD,
                    full_name=DEMO_ADMIN_FULL_NAME,
                )
            )
            summary["users_created"] = 1
            _log(f"[created]  user {user.email} (id {user.id})")
        else:
            _log(f"[exists]   user {user.email} (id {user.id})")
            if reset_demo_password:
                stored_user = db.get(User, user.id)
                stored_user.hashed_password = hash_password(DEMO_ADMIN_PASSWORD)
                stored_user.is_active = True
                db.flush()
                _log("[reset]    demo password restored to the documented demo value")
            else:
                _log(
                    "[note]     existing password left unchanged "
                    "(use --reset-demo-password to restore it)"
                )

        # 2. Demo company.  Looked up by name directly because the repository
        # exposes no name lookup and a dev database can hold thousands of rows.
        existing_company_id = db.scalar(
            select(Company.id)
            .where(Company.name == DEMO_COMPANY_NAME)
            .order_by(Company.id)
            .limit(1)
        )
        company = (
            GetCompany(company_repository).execute(existing_company_id)
            if existing_company_id is not None
            else None
        )
        if company is None:
            company = CreateCompany(company_repository).execute(
                CreateCompanyCommand(
                    name=DEMO_COMPANY_NAME,
                    base_currency=DEMO_COMPANY_CURRENCY,
                    legal_name=DEMO_COMPANY_LEGAL_NAME,
                )
            )
            summary["companies_created"] = 1
            _log(f"[created]  company {company.name} (id {company.id}, {company.base_currency})")
        else:
            _log(f"[exists]   company {company.name} (id {company.id}, {company.base_currency})")

        # 3. Admin membership for the demo user
        membership = GetCompanyUserByCompanyAndUser(company_user_repository).execute(
            company.id, user.id
        )
        if membership is None:
            membership = CreateCompanyUser(company_user_repository).execute(
                CreateCompanyUserCommand(
                    company_id=company.id,
                    user_id=user.id,
                    role=DEMO_ADMIN_ROLE,
                    is_active=True,
                )
            )
            summary["memberships_created"] = 1
            _log(f"[created]  membership role={membership.role}")
        else:
            _log(f"[exists]   membership role={membership.role} active={membership.is_active}")
            if membership.role != DEMO_ADMIN_ROLE or not membership.is_active:
                _log(
                    "[warn]     demo user is not an active admin of the demo company; "
                    "parts of the demo will be read-only"
                )

        # 4. Default chart of accounts
        seed_result = SeedDefaultAccounts(account_repository).execute(
            SeedDefaultAccountsCommand(company_id=company.id, accounts=DEFAULT_ACCOUNTS)
        )
        summary["accounts_created"] = seed_result.created_count
        summary["accounts_existing"] = seed_result.skipped_count
        _log(
            f"[accounts] {seed_result.created_count} created, "
            f"{seed_result.skipped_count} already present"
        )

        accounts_page = ListAccounts(account_repository).execute(
            company_id=company.id, skip=0, limit=500
        )
        account_ids_by_code = {account.code: account.id for account in accounts_page.items}

        # 5. Fiscal year and monthly periods
        fiscal_year = FindFiscalYearForDate(fiscal_repository).execute(company.id, year_start)
        if fiscal_year is None:
            fiscal_year = CreateFiscalYear(fiscal_repository).execute(
                CreateFiscalYearCommand(
                    company_id=company.id,
                    name=str(today.year),
                    start_date=year_start,
                    end_date=year_end,
                    status="open",
                )
            )
            summary["fiscal_years_created"] = 1
            _log(f"[created]  fiscal year {fiscal_year.name} ({fiscal_year.status})")
        else:
            _log(f"[exists]   fiscal year {fiscal_year.name} ({fiscal_year.status})")

        for period_no in range(1, 13):
            period_start, period_end = monthly_period_bounds(today.year, period_no)
            period = FindFiscalPeriodForDate(fiscal_repository).execute(
                company.id, period_start
            )
            if period is not None:
                continue
            CreateFiscalPeriod(fiscal_repository).execute(
                CreateFiscalPeriodCommand(
                    company_id=company.id,
                    fiscal_year_id=fiscal_year.id,
                    period_no=period_no,
                    name=f"{MONTH_NAMES[period_no - 1]} {today.year}",
                    start_date=period_start,
                    end_date=period_end,
                    status="open",
                )
            )
            summary["fiscal_periods_created"] += 1
        _log(
            f"[periods]  {summary['fiscal_periods_created']} created, "
            f"{12 - summary['fiscal_periods_created']} already present"
        )

        # 6. Posted journal entries
        for spec in entry_specs:
            existing_entry = GetJournalEntryByNo(journal_repository).execute(
                company.id, spec.entry_no
            )
            if existing_entry is not None:
                summary["journal_entries_existing"] += 1
                continue

            entry_year = FindFiscalYearForDate(fiscal_repository).execute(
                company.id, spec.entry_date
            )
            entry_period = FindFiscalPeriodForDate(fiscal_repository).execute(
                company.id, spec.entry_date
            )
            if entry_year is None or entry_period is None:
                raise RuntimeError(
                    f"No open fiscal year/period covers {spec.entry_date} "
                    f"for entry {spec.entry_no}"
                )
            if entry_year.status != "open" or entry_period.status != "open":
                raise RuntimeError(
                    f"Fiscal year/period for {spec.entry_date} is not open; "
                    f"cannot post {spec.entry_no}"
                )

            lines = tuple(
                CreateJournalLineCommand(
                    account_id=account_ids_by_code[line.account_code],
                    debit=line.debit,
                    credit=line.credit,
                    description=line.description,
                )
                for line in spec.lines
            )

            if spec.is_opening_balance:
                entry = CreateOpeningBalance(journal_repository).execute(
                    CreateOpeningBalanceCommand(
                        company_id=company.id,
                        fiscal_year_id=entry_year.id,
                        fiscal_period_id=entry_period.id,
                        entry_no=spec.entry_no,
                        entry_date=spec.entry_date,
                        description=spec.description,
                        created_by_user_id=user.id,
                        lines=lines,
                    )
                )
            else:
                entry = CreateJournalEntry(journal_repository).execute(
                    CreateJournalEntryCommand(
                        company_id=company.id,
                        fiscal_year_id=entry_year.id,
                        fiscal_period_id=entry_period.id,
                        entry_no=spec.entry_no,
                        entry_date=spec.entry_date,
                        description=spec.description,
                        source_type="demo_seed",
                        source_id=None,
                        created_by_user_id=user.id,
                        lines=lines,
                    )
                )

            ReviewJournalEntry(journal_repository).execute(
                ReviewJournalEntryCommand(journal_entry_id=entry.id)
            )
            PostJournalEntry(journal_repository).execute(
                PostJournalEntryCommand(journal_entry_id=entry.id)
            )
            summary["journal_entries_created"] += 1

        _log(
            f"[journals] {summary['journal_entries_created']} created and posted, "
            f"{summary['journal_entries_existing']} already present"
        )

        db.commit()
    except KeyError as error:
        db.rollback()
        print(f"\n  ERROR: demo chart of accounts is missing account code {error}.")
        print("  The demo seed expects the default chart of accounts.\n")
        raise
    except Exception as error:
        db.rollback()
        print(f"\n  ERROR: demo seed failed and was rolled back: {error}\n")
        raise
    finally:
        db.close()

    print("\n" + "-" * 64)
    print(f"  Company        : {DEMO_COMPANY_NAME} ({DEMO_COMPANY_CURRENCY})")
    print(f"  Login email    : {DEMO_ADMIN_EMAIL}")
    print(f"  Login password : {DEMO_ADMIN_PASSWORD}   (local demo only)")
    print(f"  Fiscal year    : {today.year} ({year_start} to {year_end})")
    print("-" * 64)
    print("  Demo data is ready. Open the frontend and sign in.\n")

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed local demo data for the accounting system.",
    )
    parser.add_argument(
        "--reset-demo-password",
        action="store_true",
        help=(
            "Reset the existing demo user's password back to the documented "
            "demo password. Only affects the demo user."
        ),
    )
    args = parser.parse_args()

    if is_production_environment():
        print(
            "\n  Refusing to run: APP_ENV is 'production'.\n"
            "  Demo seed data is for local development only.\n"
        )
        return 1

    try:
        seed_demo_data(reset_demo_password=args.reset_demo_password)
    except Exception:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
