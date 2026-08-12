"""Inspect and optionally remove obvious automated-test pollution from a local DB.

Dry-run is the default. Destructive execution is restricted to APP_ENV=development
and requires --confirm. This script is never imported by application startup.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

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


def print_plan(plan: CleanupPlan) -> None:
    print("\nLocal demo cleanup plan")
    print("=" * 64)
    print(f"Candidate companies : {len(plan.company_ids)}")
    print(f"Candidate test users: {len(plan.user_ids)}")
    for table, count in plan.row_counts.items():
        print(f"  {table:24} {count}")
    if plan.company_ids:
        print("\nCompanies:")
        for company_id, name in zip(plan.company_ids, plan.company_names, strict=True):
            print(f"  [{company_id}] {name}")
    if plan.user_ids:
        print("\nAutomated-test users:")
        for user_id, email in zip(plan.user_ids, plan.user_emails, strict=True):
            print(f"  [{user_id}] {email}")


def execute_cleanup(db: Session, plan: CleanupPlan) -> None:
    company_ids = plan.company_ids
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
        db.execute(delete(Company).where(Company.id.in_(company_ids)))

    for user_id in plan.user_ids:
        has_membership = db.scalar(
            select(CompanyUser.id).where(CompanyUser.user_id == user_id).limit(1)
        )
        has_conversation = db.scalar(
            select(AssistantConversation.id)
            .where(AssistantConversation.user_id == user_id)
            .limit(1)
        )
        has_invitation = db.scalar(
            select(CompanyUserInvitation.id)
            .where(
                or_(
                    CompanyUserInvitation.invited_by_user_id == user_id,
                    CompanyUserInvitation.accepted_by_user_id == user_id,
                )
            )
            .limit(1)
        )
        if not any((has_membership, has_conversation, has_invitation)):
            db.execute(delete(User).where(User.id == user_id, User.is_superuser.is_(False)))

    db.commit()


def cleanup_local_pollution(
    db: Session,
    *,
    app_env: str,
    confirm: bool = False,
    explicit_company_ids: tuple[int, ...] = (),
) -> CleanupPlan:
    ensure_cleanup_environment(app_env)
    plan = build_cleanup_plan(db, explicit_company_ids=explicit_company_ids)
    print_plan(plan)
    if not confirm:
        print("\nDRY RUN: no rows were deleted. Re-run with --confirm to apply this plan.")
        return plan
    execute_cleanup(db, plan)
    print("\nCleanup committed.")
    return plan


def main() -> int:
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
    args = parser.parse_args()
    db = SessionLocal()
    try:
        cleanup_local_pollution(
            db,
            app_env=settings.APP_ENV,
            confirm=args.confirm,
            explicit_company_ids=tuple(args.company_id),
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
