"""Create or explicitly promote the first production platform administrator."""

from __future__ import annotations

import argparse
import os
import secrets
import string
import sys
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.identity import normalize_email
from app.core.security import hash_password
from app.modules.accounting.models.audit_log import AuditLog
from app.modules.accounting.models.user import User


CONFIRMATION = "BOOTSTRAP"
FORBIDDEN_PRODUCTION_EMAILS = {"admin@example.com"}
FORBIDDEN_PRODUCTION_PASSWORDS = {"Password123", "password123"}


@dataclass(frozen=True)
class BootstrapResult:
    user_id: int
    email: str
    action: str
    temporary_password: str | None = None


def generate_temporary_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(char.islower() for char in password)
            and any(char.isupper() for char in password)
            and any(char.isdigit() for char in password)
        ):
            return password


def validate_production_identity(email: str, password: str) -> None:
    if email in FORBIDDEN_PRODUCTION_EMAILS or email.endswith("@accounting-ai-test.dev"):
        raise ValueError("Demo or automated-test email is forbidden for production bootstrap.")
    if password in FORBIDDEN_PRODUCTION_PASSWORDS:
        raise ValueError("Demo password is forbidden for production bootstrap.")
    if len(password) < 12:
        raise ValueError("Production bootstrap password must be at least 12 characters.")
    if not (
        any(char.islower() for char in password)
        and any(char.isupper() for char in password)
        and any(char.isdigit() for char in password)
    ):
        raise ValueError("Production bootstrap password must contain upper, lower, and digit.")


def bootstrap_platform_admin(
    db: Session,
    *,
    email: str,
    full_name: str | None,
    temporary_password: str | None,
    promote: bool,
    show_temporary_password: bool,
) -> BootstrapResult:
    normalized_email = normalize_email(email)
    generated_password = temporary_password or generate_temporary_password()
    validate_production_identity(normalized_email, generated_password)

    existing = db.scalar(
        select(User).where(func.lower(func.trim(User.email)) == normalized_email)
    )
    if existing is not None and existing.is_superuser:
        return BootstrapResult(existing.id, existing.email, "already_platform_admin")
    if existing is not None and not promote:
        raise ValueError(
            "User already exists and is not a platform administrator; rerun with --promote "
            "only after verifying this identity."
        )

    action = "promote_platform_admin" if existing is not None else "bootstrap_platform_admin"
    user = existing or User(email=normalized_email)
    if existing is None:
        db.add(user)
    user.full_name = full_name or user.full_name
    user.hashed_password = hash_password(generated_password)
    user.is_active = True
    user.is_superuser = True
    user.must_change_password = True
    user.token_version = (user.token_version or 0) + 1
    db.flush()

    db.add(
        AuditLog(
            company_id=None,
            actor="platform-bootstrap-cli",
            actor_user_id=user.id,
            actor_email=user.email,
            actor_name=user.full_name,
            action=action,
            entity_type="user",
            entity_id=user.id,
            new_values={"is_superuser": True, "must_change_password": True},
            description=f"Platform administrator bootstrap completed for {user.email}",
        )
    )
    db.commit()
    return BootstrapResult(
        user.id,
        user.email,
        action,
        generated_password if show_temporary_password else None,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default=os.getenv("PLATFORM_ADMIN_EMAIL"))
    parser.add_argument("--name", default=os.getenv("PLATFORM_ADMIN_NAME"))
    parser.add_argument(
        "--temporary-password",
        default=os.getenv("PLATFORM_ADMIN_TEMPORARY_PASSWORD"),
        help="Prefer PLATFORM_ADMIN_TEMPORARY_PASSWORD to avoid shell history.",
    )
    parser.add_argument("--generate-password", action="store_true")
    parser.add_argument("--show-temporary-password", action="store_true")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--confirm", choices=[CONFIRMATION])
    parser.add_argument(
        "--allow-non-production",
        action="store_true",
        help="Explicit test/staging target override; never use for routine production bootstrap.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.confirm != CONFIRMATION:
        print(f"Refusing to modify data without --confirm {CONFIRMATION}.", file=sys.stderr)
        return 2
    if settings.APP_ENV.strip().lower() != "production" and not args.allow_non_production:
        print(
            "Refusing to run outside APP_ENV=production without --allow-non-production.",
            file=sys.stderr,
        )
        return 2
    if not args.email:
        print("--email or PLATFORM_ADMIN_EMAIL is required.", file=sys.stderr)
        return 2
    if args.generate_password and args.temporary_password:
        print("Choose either a supplied password or --generate-password.", file=sys.stderr)
        return 2
    if not args.generate_password and not args.temporary_password:
        print("Supply a password or use --generate-password.", file=sys.stderr)
        return 2

    from app.core.database import SessionLocal

    try:
        with SessionLocal() as db:
            result = bootstrap_platform_admin(
                db,
                email=args.email,
                full_name=args.name,
                temporary_password=args.temporary_password,
                promote=args.promote,
                show_temporary_password=args.show_temporary_password,
            )
    except Exception as exc:
        print(f"Bootstrap refused or failed: {exc}", file=sys.stderr)
        return 1

    print(f"Platform administrator result: {result.action}; user={result.email}; id={result.user_id}")
    if result.temporary_password:
        print(f"ONE-TIME TEMPORARY PASSWORD: {result.temporary_password}")
    elif result.action != "already_platform_admin":
        print("Temporary password was not printed. Retrieve the supplied value from its secure source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
