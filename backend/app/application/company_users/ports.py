"""Company-user repository port.

Defined as ``typing.Protocol`` — never ABC — so the application layer remains
framework-neutral.
"""

from __future__ import annotations

from typing import Protocol

from app.application.company_users.dto import (
    CompanyUserDTO,
    CreateCompanyUserCommand,
    UpdateCompanyUserCommand,
)


class CompanyUserRepository(Protocol):
    def create(self, command: CreateCompanyUserCommand) -> CompanyUserDTO: ...
    def get(self, company_user_id: int) -> CompanyUserDTO | None: ...
    def get_by_company_and_user(
        self, company_id: int, user_id: int
    ) -> CompanyUserDTO | None: ...
    def update(self, command: UpdateCompanyUserCommand) -> CompanyUserDTO: ...
    def set_active(self, company_user_id: int, *, is_active: bool) -> CompanyUserDTO: ...
    def list(
        self,
        company_id: int | None = None,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CompanyUserDTO]: ...
    def count(
        self,
        company_id: int | None = None,
        user_id: int | None = None,
    ) -> int: ...
