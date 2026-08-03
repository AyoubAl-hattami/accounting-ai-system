"""
Command-line companion to the platform subscriptions page.

Covers the same operations the platform admin UI offers - list, show, activate,
suspend, cancel, extend and set-expiry - for the cases where no browser is
available (a first tenant handed over before anyone has a platform login, or a
support session over SSH).

The UI is the primary tool; this script exists so the platform is never locked
out of its own control plane.

Usage:
    cd C:\\ayoub\\accounting-ai-system\\backend
    .venv\\Scripts\\activate
    $env:PYTHONPATH = "C:\\ayoub\\accounting-ai-system\\backend"

    python scripts/manage_company_subscription.py list
    python scripts/manage_company_subscription.py list --search acme --status past_due
    python scripts/manage_company_subscription.py show --company-id 3
    python scripts/manage_company_subscription.py activate --company-id 3
    python scripts/manage_company_subscription.py extend --company-id 3 --months 1
    python scripts/manage_company_subscription.py extend --company-id 3 --years 1
    python scripts/manage_company_subscription.py set-expiry --company-id 3 --date 2026-12-31
    python scripts/manage_company_subscription.py suspend --company-id 3 --reason "non-payment"
    python scripts/manage_company_subscription.py cancel --company-id 3 --reason "churned"
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, time, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.application.subscriptions.dto import UpdateSubscriptionCommand
from app.application.subscriptions.policy import VALID_STATUSES
from app.application.subscriptions.use_cases import (
    ActivateSubscription,
    CancelSubscription,
    ExtendSubscription,
    GetCompanySubscription,
    ListCompanySubscriptions,
    SuspendSubscription,
    UpdateSubscription,
)
from app.core.database import SessionLocal
from app.infrastructure.database.sqlalchemy.repositories.subscription_repository import (
    SqlAlchemySubscriptionRepository,
)


def _format_moment(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d") if value is not None else "-"


def _print_summary(summary) -> None:
    sub = summary.subscription
    print(f"\n  Company        {summary.company_name} (ID {summary.company_id})")
    print(f"  Currency       {summary.base_currency}")
    print(f"  Members        {summary.member_count}")
    print(f"  Stored status  {sub.status}")
    print(f"  Effective      {summary.effective_status}")
    print(f"  Plan           {sub.plan_code or '-'}")
    print(f"  Expires        {_format_moment(sub.expires_at)}")
    print(f"  Days remaining {summary.days_remaining if summary.days_remaining is not None else '-'}")
    if sub.suspension_reason:
        print(f"  Reason         {sub.suspension_reason}")
    print()


def _require_company(use_case: GetCompanySubscription, company_id: int):
    summary = use_case.execute(company_id)
    if summary is None:
        print(f"\n  ✗ Company with ID {company_id} not found.\n")
        sys.exit(1)
    return summary


def _parse_expiry(value: str) -> datetime:
    """A bare date means the end of that day, matching the admin page."""
    try:
        day = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        print(f"\n  ✗ Invalid --date '{value}'. Expected YYYY-MM-DD.\n")
        sys.exit(1)
    return datetime.combine(day, time(23, 59, 59), tzinfo=timezone.utc)


def run(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        repository = SqlAlchemySubscriptionRepository(db)
        get_summary = GetCompanySubscription(repository)

        if args.command == "list":
            page = ListCompanySubscriptions(repository).execute(
                search=args.search, status=args.status, skip=0, limit=args.limit
            )
            print(f"\n  {page.total} compan{'y' if page.total == 1 else 'ies'} matched:\n")
            print(f"  {'ID':>5}  {'Name':<36}  {'Effective':<10}  {'Expires':<12}  Members")
            print("  " + "-" * 82)
            for item in page.items:
                print(
                    f"  {item.company_id:>5}  {item.company_name[:36]:<36}  "
                    f"{item.effective_status:<10}  "
                    f"{_format_moment(item.subscription.expires_at):<12}  "
                    f"{item.member_count}"
                )
            print()
            return

        summary = _require_company(get_summary, args.company_id)

        if args.command == "show":
            _print_summary(summary)
            return

        if args.command == "activate":
            ActivateSubscription(repository).execute(
                args.company_id, plan_code=args.plan_code
            )
        elif args.command == "suspend":
            SuspendSubscription(repository).execute(args.company_id, reason=args.reason)
        elif args.command == "cancel":
            CancelSubscription(repository).execute(args.company_id, reason=args.reason)
        elif args.command == "extend":
            if not args.months and not args.years:
                print("\n  ✗ Pass --months and/or --years.\n")
                sys.exit(1)
            ExtendSubscription(repository).execute(
                args.company_id, months=args.months, years=args.years
            )
        elif args.command == "set-expiry":
            UpdateSubscription(repository).execute(
                UpdateSubscriptionCommand(
                    company_id=args.company_id,
                    fields=frozenset({"expires_at"}),
                    expires_at=_parse_expiry(args.date),
                )
            )

        db.commit()
        print(f"\n  ✅ {args.command} applied.")
        _print_summary(_require_company(get_summary, args.company_id))

    except Exception as exc:  # noqa: BLE001 - a CLI reports rather than traces
        db.rollback()
        print(f"\n  ✗ Error: {exc}\n")
        sys.exit(1)
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect and control company subscriptions from the terminal.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List companies and their subscriptions.")
    list_parser.add_argument("--search", default=None, help="Filter by company name.")
    list_parser.add_argument(
        "--status", default=None, choices=sorted(VALID_STATUSES), help="Filter by effective status."
    )
    list_parser.add_argument("--limit", type=int, default=50)

    def with_company(name: str, help_text: str) -> argparse.ArgumentParser:
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("--company-id", type=int, required=True)
        return sub

    with_company("show", "Show one company's subscription.")

    activate_parser = with_company("activate", "Activate a subscription.")
    activate_parser.add_argument("--plan-code", default=None)

    suspend_parser = with_company("suspend", "Suspend a subscription.")
    suspend_parser.add_argument("--reason", default=None)

    cancel_parser = with_company("cancel", "Cancel a subscription.")
    cancel_parser.add_argument("--reason", default=None)

    extend_parser = with_company("extend", "Extend the expiry date.")
    extend_parser.add_argument("--months", type=int, default=0)
    extend_parser.add_argument("--years", type=int, default=0)

    expiry_parser = with_company("set-expiry", "Set an exact expiry date (YYYY-MM-DD).")
    expiry_parser.add_argument("--date", required=True)

    return parser


def main() -> int:
    run(build_parser().parse_args())
    return 0


if __name__ == "__main__":
    sys.exit(main())
