"""Locks an account to the password change until it completes one.

The gate hangs off ``get_current_user`` rather than off each router, so it is
deny-by-default: any endpoint that authenticates a user is covered the moment it
is written, and only the handful of paths named here stay reachable.  A route
that forgot to opt in is therefore blocked, not open.

No role escapes it.  A company admin and the platform owner are both holding a
credential that travelled over chat or email until they replace it.
"""

from fastapi import HTTPException, status

from app.modules.accounting.models.user import User

PASSWORD_CHANGE_REQUIRED_CODE = "PASSWORD_CHANGE_REQUIRED"
PASSWORD_CHANGE_REQUIRED_MESSAGE = (
    "You must change your temporary password before using the system."
)

# Exactly what the forced password change screen needs: read who you are, and
# replace the credential.  Login and logout need no token and never reach here.
ALLOWED_PATHS = frozenset(
    {
        "/auth/me",
        "/auth/change-temporary-password",
    }
)


def password_change_required_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": PASSWORD_CHANGE_REQUIRED_CODE,
            "message": PASSWORD_CHANGE_REQUIRED_MESSAGE,
        },
    )


def ensure_password_change_completed(user: User, path: str) -> None:
    """Raise 403 PASSWORD_CHANGE_REQUIRED outside the allowed paths."""
    if not user.must_change_password:
        return

    if path.rstrip("/") in ALLOWED_PATHS:
        return

    raise password_change_required_error()
