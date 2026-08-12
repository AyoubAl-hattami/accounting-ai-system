"""Inspect and optionally remove obvious automated-test pollution from a local DB.

Dry-run is the default. Destructive execution is restricted to APP_ENV=development
and requires --confirm. This script is never imported by application startup.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Iterable, TypeVar

from sqlalchemy import delete, func, or_, select, update
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
TEST_COMPANY_PREFIXES = (
    "Deterministic Company ",
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
    criteria = generated_name | fully_test_owned
    if explicit_company_ids:
        criteria = criteria | Company.id.in_(explicit_company_ids)
    return list(db.scalars(select(Company).where(criteria).order_by(Company.id)))


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
    test_users = list(
        db.scalars(
            select(User)
            .where(
                User.email.ilike(f"%{TEST_EMAIL_SUFFIX}"),
                User.is_superuser.is_(False),
            )
            .order_by(User.id)
        )
    )
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


def _delete_company_batch(db: Session, company_ids: tuple[int, ...]) -> int:
    if company_ids:
        db.execute(
            delete(AssistantConversation).where(
                AssistantConversation.company_id.in_(company_ids)
            )
        )
        db.execute(delete(JournalLine).where(JournalLine.company_id.in_(company_ids)))
        db.execute(
            update(JournalEntry)
            .where(JournalEntry.company_id.in_(company_ids))
            .values(reversal_of_id=None)
        )
        db.execute(delete(JournalEntry).where(JournalEntry.company_id.in_(company_ids)))
        db.execute(delete(AuditLog).where(AuditLog.company_id.in_(company_ids)))
        db.execute(delete(FiscalPeriod).where(FiscalPeriod.company_id.in_(company_ids)))
        db.execute(delete(FiscalYear).where(FiscalYear.company_id.in_(company_ids)))
        db.execute(
            update(Account).where(Account.company_id.in_(company_ids)).values(parent_id=None)
        )
        db.execute(delete(Account).where(Account.company_id.in_(company_ids)))
        db.execute(
            delete(CompanyUserInvitation).where(
                CompanyUserInvitation.company_id.in_(company_ids)
            )
        )
        db.execute(
            delete(CompanySubscription).where(
                CompanySubscription.company_id.in_(company_ids)
            )
        )
        db.execute(delete(CompanyUser).where(CompanyUser.company_id.in_(company_ids)))
        result = db.execute(delete(Company).where(Company.id.in_(company_ids)))
        return int(result.rowcount or 0)
    return 0


def _delete_user_batch(db: Session, user_ids: tuple[int, ...]) -> int:
    if not user_ids:
        return 0
    has_membership = select(CompanyUser.id).where(CompanyUser.user_id == User.id)
    has_conversation = select(AssistantConversation.id).where(
        AssistantConversation.user_id == User.id
    )
    has_invitation = select(CompanyUserInvitation.id).where(
        CompanyUserInvitation.invited_by_user_id == User.id
    )
    result = db.execute(
        delete(User).where(
            User.id.in_(user_ids),
            User.email.ilike(f"%{TEST_EMAIL_SUFFIX}"),
            User.is_superuser.is_(False),
            ~has_membership.exists(),
            ~has_conversation.exists(),
            ~has_invitation.exists(),
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
            except Exception:
                db.rollback()
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
