"""Company-user application use cases."""

from __future__ import annotations

from app.application.company_users.dto import (
    CompanyUserDTO,
    CompanyUserPageDTO,
    CreateCompanyUserCommand,
    UpdateCompanyUserCommand,
)
from app.application.company_users.ports import CompanyUserRepository


class CreateCompanyUser:
    def __init__(self, repository: CompanyUserRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateCompanyUserCommand) -> CompanyUserDTO:
        return self._repository.create(command)


class GetCompanyUser:
    def __init__(self, repository: CompanyUserRepository) -> None:
        self._repository = repository

    def execute(self, company_user_id: int) -> CompanyUserDTO | None:
        return self._repository.get(company_user_id)


class GetCompanyUserByCompanyAndUser:
    def __init__(self, repository: CompanyUserRepository) -> None:
        self._repository = repository

    def execute(self, company_id: int, user_id: int) -> CompanyUserDTO | None:
        return self._repository.get_by_company_and_user(company_id, user_id)


class UpdateCompanyUser:
    def __init__(self, repository: CompanyUserRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateCompanyUserCommand) -> CompanyUserDTO:
        return self._repository.update(command)


class SetCompanyUserActive:
    def __init__(self, repository: CompanyUserRepository) -> None:
        self._repository = repository

    def execute(self, company_user_id: int, *, is_active: bool) -> CompanyUserDTO:
        return self._repository.set_active(company_user_id, is_active=is_active)


class ListCompanyUsers:
    def __init__(self, repository: CompanyUserRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        company_id: int | None = None,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> CompanyUserPageDTO:
        items = self._repository.list(
            company_id=company_id, user_id=user_id, skip=skip, limit=limit
        )
        total = self._repository.count(company_id=company_id, user_id=user_id)
        return CompanyUserPageDTO(items=tuple(items), total=total, skip=skip, limit=limit)
