"""
Command-line companion to the client onboarding wizard.

Creates a tenant, its first administrator, and its subscription in one
transaction, exactly as POST /platform/onboarding/clients does, for the cases
where no browser is available: the very first client handed over before anyone
has a platform login, or a support session over SSH.

The wizard is the primary tool; this script exists so the platform is never
locked out of its own control plane.

The temporary password is printed once, inside the handover message, and is
never written to the audit log. Treat the terminal output accordingly - do not
pipe it into a file that outlives the handover.

Usage:
    cd C:\\ayoub\\accounting-ai-system\\backend
    .venv\\Scripts\\activate
    $env:PYTHONPATH = "C:\\ayoub\\accounting-ai-system\\backend"

    python scripts/onboard_client.py --company-name "Acme Trading" \\
        --admin-email admin@acme.com --expires 2027-01-31

    python scripts/onboard_client.py --company-name "Acme Trading" \\
        --admin-email admin@acme.com --trial-ends 2026-09-30 --status trial

    python scripts/onboard_client.py --company-name "Acme Trading" \\
        --admin-email admin@acme.com --expires 2027-01-31 \\
        --password "Str0ngHandover" --no-fiscal-year
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, time, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.application.onboarding.dto import OnboardClientCommand
from app.application.onboarding.errors import OnboardingError
from app.application.onboarding.handover import build_handover_message
from app.application.onboarding.passwords import generate_temporary_password
from app.application.onboarding.use_cases import OnboardClient
from app.core.database import SessionLocal
from app.core.public_url import is_public_url_configured, public_login_url
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
from app.infrastructure.database.sqlalchemy.repositories.subscription_repository import (
    SqlAlchemySubscriptionRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from app.modules.accounting.schemas.client_onboarding import DEFAULT_PLAN_CODE
from app.modules.accounting.services.audit_service import prepare_audit_log


def _parse_day(value: str, flag: str) -> datetime:
    """A bare date means the end of that day, matching the wizard."""
    try:
        day = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        print(f"\n  x Invalid {flag} '{value}'. Expected YYYY-MM-DD.\n")
        sys.exit(1)
    return datetime.combine(day, time(23, 59, 59), tzinfo=timezone.utc)


def run(args: argparse.Namespace) -> None:
    if args.password and args.generate_password:
        print("\n  x Pass either --password or --generate-password, not both.\n")
        sys.exit(1)

    if not args.expires and not args.trial_ends:
        print("\n  x Pass --expires and/or --trial-ends.\n")
        sys.exit(1)

    # Generating is the default: an operator who supplies nothing should still
    # end up with a password strong enough for the account policy.
    temporary_password = args.password or (
        None if args.reuse_existing_user else generate_temporary_password()
    )

    db = SessionLocal()
    try:
        use_case = OnboardClient(
            companies=SqlAlchemyCompanyRepository(db),
            users=SqlAlchemyUserRepository(db),
            company_users=SqlAlchemyCompanyUserRepository(db),
            subscriptions=SqlAlchemySubscriptionRepository(db),
            accounts=SqlAlchemyAccountRepository(db),
            fiscal=SqlAlchemyFiscalRepository(db),
        )

        result = use_case.execute(
            OnboardClientCommand(
                company_name=args.company_name,
                base_currency=args.currency.upper(),
                admin_email=args.admin_email.strip().lower(),
                temporary_password=temporary_password or "",
                admin_full_name=args.admin_name,
                plan_code=args.plan_code,
                subscription_status=args.status,
                subscription_expires_at=(
                    _parse_day(args.expires, "--expires") if args.expires else None
                ),
                trial_ends_at=(
                    _parse_day(args.trial_ends, "--trial-ends")
                    if args.trial_ends
                    else None
                ),
                seed_default_accounts=not args.no_seed_accounts,
                create_fiscal_year=not args.no_fiscal_year,
                open_monthly_periods=not args.no_fiscal_year
                and not args.no_monthly_periods,
                reuse_existing_user=args.reuse_existing_user,
                onboarding_note=args.note,
            )
        )

        handover_password = (
            temporary_password if not result.admin_was_existing else None
        )

        prepare_audit_log(
            db=db,
            company_id=result.company_id,
            actor="cli",
            actor_user_id=None,
            actor_email=None,
            actor_name="onboard_client.py",
            action="onboard_client",
            entity_type="client_onboarding",
            entity_id=result.company_id,
            # No password, generated or supplied, is ever recorded here.
            new_values={
                "company_name": result.company_name,
                "base_currency": result.base_currency,
                "admin_email": result.admin_email,
                "admin_user_id": result.admin_user_id,
                "admin_was_existing": result.admin_was_existing,
                "plan_code": result.plan_code,
                "subscription_status": result.subscription_status,
                "expires_at": (
                    result.expires_at.isoformat() if result.expires_at else None
                ),
                "seeded_accounts_count": result.seeded_accounts_count,
                "fiscal_year_created": result.fiscal_year_created,
                "fiscal_periods_created": result.fiscal_periods_created,
                "onboarding_note": args.note,
            },
            description=(
                f"Onboarded client '{result.company_name}' with admin "
                f"{result.admin_email}"
            ),
        )
        db.commit()

    except OnboardingError as error:
        db.rollback()
        print(f"\n  x Refused: {error}\n")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001 - a CLI reports rather than traces
        db.rollback()
        print(f"\n  x Error: {exc}\n")
        sys.exit(1)
    finally:
        db.close()

    login_url = public_login_url()

    print("\n  Client onboarded.\n")
    print(f"  Company ID        {result.company_id}")
    print(f"  Admin user ID     {result.admin_user_id}")
    print(f"  Effective status  {result.effective_status}")
    print(f"  Accounts seeded   {result.seeded_accounts_count}")
    print(f"  Fiscal year       {'created' if result.fiscal_year_created else 'not created'}")
    print(f"  Fiscal periods    {result.fiscal_periods_created}")
    print(f"  Login URL         {login_url}")

    if not is_public_url_configured():
        print(
            "\n  ! APP_PUBLIC_URL is not set, so the handover message below "
            "carries a placeholder\n"
            "    instead of a real address. Set it before sending the message."
        )

    if handover_password:
        print(
            "\n  ! The temporary password is shown once, in the message below. "
            "The admin must\n"
            "    change it at first login before anything else opens."
        )

    print("\n  ---------------- handover message ----------------\n")
    print(
        build_handover_message(
            company_name=result.company_name,
            admin_email=result.admin_email,
            temporary_password=handover_password,
            expires_at=result.expires_at,
            login_url=login_url,
        )
    )
    print("\n  --------------------------------------------------\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Onboard a client company from the terminal.",
    )
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--currency", default="USD", help="Three-letter ISO code.")
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-name", default=None)

    parser.add_argument(
        "--password",
        default=None,
        help="Temporary password. Omit to have one generated.",
    )
    parser.add_argument(
        "--generate-password",
        action="store_true",
        help="Explicitly generate the password (the default when --password is omitted).",
    )
    parser.add_argument(
        "--reuse-existing-user",
        action="store_true",
        help="Attach an account that already exists instead of refusing.",
    )

    parser.add_argument("--plan-code", default=DEFAULT_PLAN_CODE)
    parser.add_argument("--status", default="active", choices=["active", "trial"])
    parser.add_argument("--expires", default=None, help="YYYY-MM-DD.")
    parser.add_argument("--trial-ends", default=None, help="YYYY-MM-DD.")

    parser.add_argument("--no-seed-accounts", action="store_true")
    parser.add_argument("--no-fiscal-year", action="store_true")
    parser.add_argument("--no-monthly-periods", action="store_true")
    parser.add_argument("--note", default=None, help="Recorded in the audit log.")

    return parser


def main() -> int:
    run(build_parser().parse_args())
    return 0


if __name__ == "__main__":
    sys.exit(main())
