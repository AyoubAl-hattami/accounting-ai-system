"""User application use cases."""

from __future__ import annotations

from app.application.users.dto import (
    AuthenticateUserCommand,
    CreateUserCommand,
    SetUserActiveCommand,
    UserDTO,
)
from app.application.users.ports import UserRepository


class AuthenticateUser:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(self, command: AuthenticateUserCommand) -> UserDTO | None:
        return self._repository.authenticate(command.email, command.password)


class GetUser:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(self, user_id: int) -> UserDTO | None:
        return self._repository.get(user_id)


class LookupUserByEmail:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(self, email: str) -> UserDTO | None:
        return self._repository.get_by_email(email)


class CreateUser:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateUserCommand) -> UserDTO:
        return self._repository.create(command)


class SetUserActive:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(self, command: SetUserActiveCommand) -> UserDTO:
        return self._repository.set_active(command)
