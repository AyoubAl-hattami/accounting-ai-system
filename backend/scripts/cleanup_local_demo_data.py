"""Inspect and optionally remove obvious automated-test pollution from a local DB.

Dry-run is the default. Destructive execution is restricted to APP_ENV=development
and requires --confirm. This script is never imported by application startup.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from typing import Iterable, TypeVar

from sqlalchemy import bindparam, delete, func, inspect, or_, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.assistant_conversation import (
    AssistantConversation,
)
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


TEST_EMAIL_SUFFIX = "@accounting-ai-test.dev"
EXAMPLE_TEST_EMAIL_SUFFIX = "@example.com"
EXAMPLE_TEST_EMAIL_PREFIXES = (
    "cross_tenant_",
    "same_company_",
    "admin_a_",
    "admin_b_",
    "user_a_",
    "user_b_",
    "test_",
)
TEST_COMPANY_PREFIXES = (
    "CrossTenant",
    "SameCompany",
    "CompanyA_",
    "CompanyB_",
    "Deterministic Company",
    "Test Company",
    "BS Multi Year ",
    "CLI Client ",
    "SoleCo_",
    "RoleCompany_",
    "OverlapCreate_",
    "QuickSetupClosedPeriod_",
    "AdjacentPeriod_",
    "PeriodCompanyA_",
    "PeriodCompanyB_",
    "OverlapUpdate_",
    "QuickSetupCreate_",
    "QuickSetupIdempotent_",
    "QuickSetupLockedYear_",
    "ExplainProfit_",
    "FiscalYearCreate_",
    "FiscalPeriodCreate_",
    "FiscalYearAudit_",
    "Account roles_",
    "Update roles_",
    "Invite Company ",
    "Account create_",
    "Account validation first_",
    "Account validation second_",
    "Account update_",
    "Update validation first_",
    "Update validation second_",
    "Update system_",
    "AccountAuditCo_",
    "AccountUpdateAuditCo_",
    "Seed idempotency_",
    "Journal create roles_",
    "Journal write roles_",
    "Journal read roles_",
    "Journal inactive_",
    "Journal code first_",
    "Journal code second_",
    "Journal accounts_",
    "Journal archive_",
    "Journal seed_",
    "Journal preview_",
    "Journal filters_",
    "Seed defaults_",
    "Journal access isolation_",
    "Conversation Company ",
    "Tenant Co ",
    "AuditTestCo_",
    "SeedAuditCo_",
    "UpdAuditCo_",
    "Filter trial ",
    "Filter active ",
    "Filter past_due ",
    "Filter suspended ",
    "Filter cancelled ",
    "Recent Client ",
)
DEFAULT_BATCH_SIZE = 100
SAMPLE_SIZE = 5
T = TypeVar("T")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Fixed child-to-parent order. Some tables belong to later local phases and may
# not exist on this branch; the deletion helper checks both table and company_id
# column presence before issuing SQL.
COMPANY_DEPENDENT_TABLES = (
    "journal_lines",
    "assistant_conversations",
    "journal_entries",
    "journals",
    "audit_logs",
    "exchange_rates",
    "fiscal_periods",
    "fiscal_years",
    "accounts",
    "company_user_invitations",
    "company_invitations",
    "invitations",
    "company_subscriptions",
    "company_users",
)
JOURNAL_CHILD_TABLES = ("journal_sequences",)
USER_DEPENDENT_TABLE_COLUMNS = (
    ("assistant_conversations", ("user_id",)),
    ("audit_logs", ("actor_user_id", "created_by_user_id", "user_id")),
    (
        "company_user_invitations",
        (
            "invited_by_user_id",
            "accepted_by_user_id",
            "cancelled_by_user_id",
            "user_id",
        ),
    ),
    (
        "company_invitations",
        ("invited_by_user_id", "accepted_by_user_id", "user_id"),
    ),
    ("invitations", ("invited_by_user_id", "accepted_by_user_id", "user_id")),
    ("password_reset_tokens", ("user_id",)),
    ("user_password_reset_tokens", ("user_id",)),
    ("auth_tokens", ("user_id",)),
    ("access_tokens", ("user_id",)),
    ("refresh_tokens", ("user_id",)),
    ("user_sessions", ("user_id",)),
    ("sessions", ("user_id",)),
    ("company_users", ("user_id",)),
)


@dataclass(frozen=True, slots=True)
class CleanupPlan:
    company_ids: tuple[int, ...]
    company_names: tuple[str, ...]
    user_ids: tuple[int, ...]
    user_emails: tuple[str, ...]
    row_counts: dict[str, int]


def ensure_cleanup_environment(app_env: str) -> None:
    if app_env.strip().lower() != "development":
        raise RuntimeError(
            "Local demo cleanup is allowed only when APP_ENV=development."
        )


def _candidate_companies(
    db: Session, explicit_company_ids: tuple[int, ...]
) -> list[Company]:
    test_member = (
        select(CompanyUser.company_id)
        .join(User, User.id == CompanyUser.user_id)
        .where(User.email.ilike(f"%{TEST_EMAIL_SUFFIX}"))
    )
    non_test_member = (
        select(CompanyUser.company_id)
        .join(User, User.id == CompanyUser.user_id)
        .where(~User.email.ilike(f"%{TEST_EMAIL_SUFFIX}"))
    )
    generated_name = or_(
        *(Company.name.startswith(prefix) for prefix in TEST_COMPANY_PREFIXES)
    )
    fully_test_owned = Company.id.in_(test_member) & ~Company.id.in_(non_test_member)
    has_membership = select(CompanyUser.id).where(
        CompanyUser.company_id == Company.id
    ).exists()
    has_account = select(Account.id).where(Account.company_id == Company.id).exists()
    has_journal_entry = select(JournalEntry.id).where(
        JournalEntry.company_id == Company.id
    ).exists()
    has_subscription = select(CompanySubscription.id).where(
        CompanySubscription.company_id == Company.id
    ).exists()
    empty_other_co_test_fixture = (
        (Company.name == "Other Co")
        & ~has_membership
        & ~has_account
        & ~has_journal_entry
        & has_subscription
    )
    criteria = generated_name | fully_test_owned | empty_other_co_test_fixture
    if explicit_company_ids:
        criteria = criteria | Company.id.in_(explicit_company_ids)
    return list(db.scalars(select(Company).where(criteria).order_by(Company.id)))


def _candidate_users(db: Session, company_ids: tuple[int, ...]) -> list[User]:
    known_example_identity = or_(
        *(
            User.email.ilike(f"{prefix}%{EXAMPLE_TEST_EMAIL_SUFFIX}")
            for prefix in EXAMPLE_TEST_EMAIL_PREFIXES
        )
    )
    attached_to_test_company = False
    if company_ids:
        attached_to_test_company = User.id.in_(
            select(CompanyUser.user_id).where(CompanyUser.company_id.in_(company_ids))
        )
    criteria = User.email.ilike(f"%{TEST_EMAIL_SUFFIX}") | (
        User.email.ilike(f"%{EXAMPLE_TEST_EMAIL_SUFFIX}")
        & (known_example_identity | attached_to_test_company)
    )
    return list(
        db.scalars(
            select(User)
            .where(criteria, User.is_superuser.is_(False))
            .order_by(User.id)
        )
    )


def _count(db: Session, model, company_ids: tuple[int, ...]) -> int:
    if not company_ids:
        return 0
    return int(
        db.scalar(
            select(func.count()).select_from(model).where(model.company_id.in_(company_ids))
        )
        or 0
    )


def build_cleanup_plan(
    db: Session, *, explicit_company_ids: tuple[int, ...] = ()
) -> CleanupPlan:
    companies = _candidate_companies(db, explicit_company_ids)
    company_ids = tuple(company.id for company in companies)
    test_users = _candidate_users(db, company_ids)
    counts = {
        "assistant_conversations": _count(db, AssistantConversation, company_ids),
        "journal_entries": _count(db, JournalEntry, company_ids),
        "journal_lines": _count(db, JournalLine, company_ids),
        "accounts": _count(db, Account, company_ids),
        "fiscal_periods": _count(db, FiscalPeriod, company_ids),
        "fiscal_years": _count(db, FiscalYear, company_ids),
        "audit_logs": _count(db, AuditLog, company_ids),
        "invitations": _count(db, CompanyUserInvitation, company_ids),
        "subscriptions": _count(db, CompanySubscription, company_ids),
        "memberships": _count(db, CompanyUser, company_ids),
    }
    return CleanupPlan(
        company_ids=company_ids,
        company_names=tuple(company.name for company in companies),
        user_ids=tuple(user.id for user in test_users),
        user_emails=tuple(user.email for user in test_users),
        row_counts=counts,
    )


def _emit(message: str = "") -> None:
    print(message, flush=True)


def _batches(items: tuple[T, ...], batch_size: int) -> Iterable[tuple[T, ...]]:
    for offset in range(0, len(items), batch_size):
        yield items[offset : offset + batch_size]


def _print_identifiers(
    heading: str,
    identifiers: tuple[int, ...],
    labels: tuple[str, ...],
    *,
    verbose: bool,
) -> None:
    if not identifiers:
        return
    pairs = list(zip(identifiers, labels, strict=True))
    if verbose or len(pairs) <= SAMPLE_SIZE * 2:
        displayed = pairs
    else:
        displayed = pairs[:SAMPLE_SIZE] + pairs[-SAMPLE_SIZE:]
    _emit(f"\n{heading}:")
    for identifier, label in displayed:
        _emit(f"  [{identifier}] {label}")
    hidden = len(pairs) - len(displayed)
    if hidden:
        _emit(f"  ... {hidden} more (use --verbose to print every identifier)")


def print_plan(plan: CleanupPlan, *, verbose: bool = False) -> None:
    _emit("\nLocal demo cleanup plan")
    _emit("=" * 64)
    _emit(f"Candidate companies : {len(plan.company_ids)}")
    _emit(f"Candidate test users: {len(plan.user_ids)}")
    _emit(f"Total candidates    : {len(plan.company_ids) + len(plan.user_ids)}")
    for table, count in plan.row_counts.items():
        _emit(f"  {table:24} {count}")
    _print_identifiers(
        "Companies",
        plan.company_ids,
        plan.company_names,
        verbose=verbose,
    )
    _print_identifiers(
        "Automated-test users",
        plan.user_ids,
        plan.user_emails,
        verbose=verbose,
    )


def _safe_table_name(table_name: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(table_name):
        raise ValueError(f"Unsafe internal table name: {table_name!r}")
    return table_name


def _table_columns(schema_inspector, table_name: str) -> set[str]:
    table_name = _safe_table_name(table_name)
    if not schema_inspector.has_table(table_name):
        return set()
    return {column["name"] for column in schema_inspector.get_columns(table_name)}


def _delete_company_rows_if_table_exists(
    db: Session,
    schema_inspector,
    table_name: str,
    company_ids: tuple[int, ...],
) -> int:
    """Delete tenant rows from one known table without assuming its migration exists."""
    if not company_ids or "company_id" not in _table_columns(
        schema_inspector, table_name
    ):
        return 0
    table_name = _safe_table_name(table_name)
    statement = text(
        f'DELETE FROM "{table_name}" WHERE company_id IN :company_ids'
    ).bindparams(bindparam("company_ids", expanding=True))
    result = db.execute(statement, {"company_ids": company_ids})
    return int(result.rowcount or 0)


def _delete_journal_children_if_tables_exist(
    db: Session,
    schema_inspector,
    table_name: str,
    company_ids: tuple[int, ...],
) -> int:
    """Delete rows linked to legacy journals through journal_id."""
    child_columns = _table_columns(schema_inspector, table_name)
    journal_columns = _table_columns(schema_inspector, "journals")
    if (
        not company_ids
        or "journal_id" not in child_columns
        or not {"id", "company_id"}.issubset(journal_columns)
    ):
        return 0
    table_name = _safe_table_name(table_name)
    statement = text(
        f'DELETE FROM "{table_name}" WHERE journal_id IN ('
        'SELECT id FROM "journals" WHERE company_id IN :company_ids'
        ")"
    ).bindparams(bindparam("company_ids", expanding=True))
    result = db.execute(statement, {"company_ids": company_ids})
    return int(result.rowcount or 0)


def _delete_user_rows_if_table_exists(
    db: Session,
    schema_inspector,
    table_name: str,
    candidate_columns: tuple[str, ...],
    user_ids: tuple[int, ...],
) -> int:
    """Delete rows tied to selected test users through any known user column."""
    if not user_ids:
        return 0
    existing_columns = _table_columns(schema_inspector, table_name)
    matched_columns = tuple(
        _safe_table_name(column_name)
        for column_name in candidate_columns
        if column_name in existing_columns
    )
    if not matched_columns:
        return 0
    table_name = _safe_table_name(table_name)
    predicates = " OR ".join(
        f'"{column_name}" IN :user_ids' for column_name in matched_columns
    )
    statement = text(f'DELETE FROM "{table_name}" WHERE {predicates}').bindparams(
        bindparam("user_ids", expanding=True)
    )
    result = db.execute(statement, {"user_ids": user_ids})
    return int(result.rowcount or 0)


def _clear_self_reference_if_table_exists(
    db: Session,
    schema_inspector,
    table_name: str,
    column_name: str,
    company_ids: tuple[int, ...],
) -> None:
    columns = _table_columns(schema_inspector, table_name)
    if "company_id" not in columns or column_name not in columns:
        return
    table_name = _safe_table_name(table_name)
    column_name = _safe_table_name(column_name)
    statement = text(
        f'UPDATE "{table_name}" SET "{column_name}" = NULL '
        "WHERE company_id IN :company_ids"
    ).bindparams(bindparam("company_ids", expanding=True))
    db.execute(statement, {"company_ids": company_ids})


def _delete_company_batch(db: Session, company_ids: tuple[int, ...]) -> int:
    if not company_ids:
        return 0

    schema_inspector = inspect(db.connection())
    _clear_self_reference_if_table_exists(
        db,
        schema_inspector,
        "journal_entries",
        "reversal_of_id",
        company_ids,
    )
    _clear_self_reference_if_table_exists(
        db,
        schema_inspector,
        "accounts",
        "parent_id",
        company_ids,
    )
    for table_name in COMPANY_DEPENDENT_TABLES:
        if table_name == "journals":
            for child_table_name in JOURNAL_CHILD_TABLES:
                _delete_journal_children_if_tables_exist(
                    db,
                    schema_inspector,
                    child_table_name,
                    company_ids,
                )
        _delete_company_rows_if_table_exists(
            db,
            schema_inspector,
            table_name,
            company_ids,
        )

    result = db.execute(delete(Company).where(Company.id.in_(company_ids)))
    return int(result.rowcount or 0)


def _foreign_key_blocker(error: Exception) -> str:
    original = getattr(error, "orig", None)
    diagnostics = getattr(original, "diag", None)
    table_name = getattr(diagnostics, "table_name", None)
    constraint_name = getattr(diagnostics, "constraint_name", None)
    detail = getattr(diagnostics, "message_detail", None)
    parts = ["foreign-key restriction"]
    if table_name:
        parts.append(f"table={table_name}")
    if constraint_name:
        parts.append(f"constraint={constraint_name}")
    if detail:
        parts.append(f"detail={detail}")
    elif original:
        parts.append(str(original).strip())
    else:
        parts.append(str(error).strip())
    return "; ".join(parts)


def _delete_user_batch(db: Session, user_ids: tuple[int, ...]) -> int:
    if not user_ids:
        return 0

    schema_inspector = inspect(db.connection())
    for table_name, candidate_columns in USER_DEPENDENT_TABLE_COLUMNS:
        _delete_user_rows_if_table_exists(
            db,
            schema_inspector,
            table_name,
            candidate_columns,
            user_ids,
        )

    result = db.execute(
        delete(User).where(
            User.id.in_(user_ids),
            or_(
                User.email.ilike(f"%{TEST_EMAIL_SUFFIX}"),
                User.email.ilike(f"%{EXAMPLE_TEST_EMAIL_SUFFIX}"),
            ),
            User.is_superuser.is_(False),
        )
    )
    return int(result.rowcount or 0)


def execute_cleanup(
    db: Session,
    plan: CleanupPlan,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    verbose: bool = False,
) -> int:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    total = len(plan.company_ids) + len(plan.user_ids)
    total_batches = (
        (len(plan.company_ids) + batch_size - 1) // batch_size
        + (len(plan.user_ids) + batch_size - 1) // batch_size
    )
    processed = 0
    deleted = 0
    batch_number = 0

    _emit(f"\nStarting confirmed cleanup: {total} candidates in {total_batches} batches.")

    for kind, identifiers, labels, delete_batch in (
        ("companies", plan.company_ids, plan.company_names, _delete_company_batch),
        ("users", plan.user_ids, plan.user_emails, _delete_user_batch),
    ):
        label_by_id = dict(zip(identifiers, labels, strict=True))
        for batch in _batches(identifiers, batch_size):
            batch_number += 1
            _emit(
                f"Batch {batch_number}/{total_batches}: deleting up to "
                f"{len(batch)} {kind}..."
            )
            if verbose:
                for identifier in batch:
                    _emit(f"  [{identifier}] {label_by_id[identifier]}")
            try:
                batch_deleted = delete_batch(db, batch)
                db.commit()
            except Exception as error:
                db.rollback()
                _emit(
                    f"Batch {batch_number}/{total_batches} rolled back; "
                    f"blocker: {_foreign_key_blocker(error)}"
                )
                raise
            processed += len(batch)
            deleted += batch_deleted
            _emit(
                f"Batch {batch_number}/{total_batches} committed: "
                f"deleted {batch_deleted}; deleted total {deleted}; "
                f"remaining candidates {total - processed}."
            )

    _emit(f"Cleanup complete: deleted {deleted} of {total} candidates.")
    return deleted


def cleanup_local_pollution(
    db: Session,
    *,
    app_env: str,
    confirm: bool = False,
    explicit_company_ids: tuple[int, ...] = (),
    batch_size: int = DEFAULT_BATCH_SIZE,
    verbose: bool = False,
) -> CleanupPlan:
    ensure_cleanup_environment(app_env)
    plan = build_cleanup_plan(db, explicit_company_ids=explicit_company_ids)
    print_plan(plan, verbose=verbose)
    if not confirm:
        _emit("\nDRY RUN: no rows were deleted. Re-run with --confirm to apply this plan.")
        return plan
    execute_cleanup(db, plan, batch_size=batch_size, verbose=verbose)
    return plan


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm", action="store_true", help="Commit the printed cleanup plan."
    )
    parser.add_argument(
        "--company-id",
        type=int,
        action="append",
        default=[],
        help="Explicit local company ID to include; repeat for multiple IDs.",
    )
    parser.add_argument(
        "--batch-size",
        type=_positive_int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Candidates committed per batch (default: {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every candidate identifier instead of a short sample.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    db = SessionLocal()
    try:
        cleanup_local_pollution(
            db,
            app_env=settings.APP_ENV,
            confirm=args.confirm,
            explicit_company_ids=tuple(args.company_id),
            batch_size=args.batch_size,
            verbose=args.verbose,
        )
    except Exception as error:
        db.rollback()
        print(f"\nCleanup refused or failed: {error}", file=sys.stderr)
        return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
