"""User repository port.

Defined as ``typing.Protocol`` — never ABC — so the application layer remains
framework-neutral.
"""

from __future__ import annotations

from typing import Protocol

from app.application.users.dto import CreateUserCommand, SetUserActiveCommand, UserDTO


class UserRepository(Protocol):
    def get(self, user_id: int) -> UserDTO | None: ...
    def get_by_email(self, email: str) -> UserDTO | None: ...
    def create(self, command: CreateUserCommand) -> UserDTO: ...
    def authenticate(self, email: str, password: str) -> UserDTO | None: ...
    def set_active(self, command: SetUserActiveCommand) -> UserDTO: ...
    def count_active_superusers(self) -> int: ...
