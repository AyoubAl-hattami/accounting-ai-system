"""Framework-neutral data transfer objects for user use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class UserDTO:
    """Read projection of a persisted user record."""

    id: int
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    full_name: str | None = None
    must_change_password: bool = False
    token_version: int = 0


@dataclass(frozen=True, slots=True)
class SetUserActiveCommand:
    user_id: int
    is_active: bool


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    email: str
    password: str
    full_name: str | None = None
    must_change_password: bool = False


@dataclass(frozen=True, slots=True)
class AuthenticateUserCommand:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class ChangePasswordCommand:
    """Replace a password the holder can already prove they know.

    Both values are plaintext in memory for the length of one request and are
    never persisted, logged, or echoed back.
    """

    user_id: int
    current_password: str
    new_password: str
