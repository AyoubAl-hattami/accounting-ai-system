"""Infrastructure token generation for authenticated users."""

from __future__ import annotations

from app.application.users.dto import UserDTO
from app.core.security import create_access_token, verify_password


def generate_user_token(user: UserDTO) -> str:
    """Create a signed JWT access token for the given user DTO."""
    return create_access_token(
        subject=user.id,
        extra_claims={
            "email": user.email,
            "is_superuser": user.is_superuser,
        },
    )


def check_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches hashed_password."""
    return verify_password(
        plain_password=plain_password,
        hashed_password=hashed_password,
    )
