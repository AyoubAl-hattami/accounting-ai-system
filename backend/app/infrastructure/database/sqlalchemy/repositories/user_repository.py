"""SQLAlchemy implementation of the user repository port."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.users.dto import (
    ChangePasswordCommand,
    CreateUserCommand,
    SetUserActiveCommand,
    UserDTO,
)
from app.application.users.errors import (
    CurrentPasswordMismatch,
    NewPasswordReused,
    UserNotFound,
)
from app.core.identity import normalize_email
from app.core.security import hash_password, verify_password
from app.application.users.ports import UserRepository
from app.core.database import flush_or_rollback
from app.modules.accounting.models.user import User


class SqlAlchemyUserRepository:
    """Implements UserRepository.  Flushes but does not commit."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _to_dto(user: User) -> UserDTO:
        return UserDTO(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at,
            must_change_password=user.must_change_password,
            token_version=user.token_version,
        )

    def get_by_email(self, email: str) -> UserDTO | None:
        normalized = normalize_email(email)
        user = self._db.scalar(
            select(User).where(func.lower(func.trim(User.email)) == normalized)
        )
        return self._to_dto(user) if user is not None else None

    def create(self, command: CreateUserCommand) -> UserDTO:
        user = User(
            email=normalize_email(command.email),
            full_name=command.full_name,
            hashed_password=hash_password(command.password),
            is_active=True,
            is_superuser=False,
            must_change_password=command.must_change_password,
        )
        self._db.add(user)
        flush_or_rollback(self._db)
        return self._to_dto(user)

    def authenticate(self, email: str, password: str) -> UserDTO | None:
        """Return the user DTO if credentials are valid and account is active, else None."""
        normalized = normalize_email(email)
        user = self._db.scalar(
            select(User).where(func.lower(func.trim(User.email)) == normalized)
        )
        if user is None or not user.is_active:
            return None
        if not verify_password(plain_password=password, hashed_password=user.hashed_password):
            return None
        return self._to_dto(user)

    def get(self, user_id: int) -> UserDTO | None:
        user = self._db.scalar(select(User).where(User.id == user_id))
        return self._to_dto(user) if user is not None else None

    def set_active(self, command: SetUserActiveCommand) -> UserDTO:
        user = self._db.scalar(select(User).where(User.id == command.user_id))
        if user is None:
            raise ValueError(f"User {command.user_id} not found")
        if user.is_active != command.is_active:
            user.is_active = command.is_active
            user.token_version += 1
        self._db.add(user)
        flush_or_rollback(self._db)
        return self._to_dto(user)

    def change_password(self, command: ChangePasswordCommand) -> UserDTO:
        user = self._db.scalar(select(User).where(User.id == command.user_id))
        if user is None:
            raise UserNotFound(str(command.user_id))

        if not verify_password(
            plain_password=command.current_password,
            hashed_password=user.hashed_password,
        ):
            raise CurrentPasswordMismatch()

        if verify_password(
            plain_password=command.new_password,
            hashed_password=user.hashed_password,
        ):
            raise NewPasswordReused()

        user.hashed_password = hash_password(command.new_password)
        user.must_change_password = False
        user.token_version += 1
        self._db.add(user)
        flush_or_rollback(self._db)
        return self._to_dto(user)

    def count_active_superusers(self) -> int:
        return int(
            self._db.scalar(
                select(func.count()).select_from(User).where(
                    User.is_superuser.is_(True),
                    User.is_active.is_(True),
                )
            ) or 0
        )
