"""Company application use cases."""

from __future__ import annotations

from app.application.companies.dto import (
    CompanyDTO,
    CompanyPageDTO,
    CreateCompanyCommand,
    UpdateCompanyCommand,
)
from app.application.companies.ports import CompanyRepository


class CreateCompany:
    def __init__(self, repository: CompanyRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateCompanyCommand) -> CompanyDTO:
        normalized = CreateCompanyCommand(
            name=command.name.strip(),
            base_currency=command.base_currency.upper(),
            legal_name=command.legal_name,
            registration_no=command.registration_no,
            tax_no=command.tax_no,
            address=command.address,
            is_active=command.is_active,
        )
        return self._repository.create(normalized)


class GetCompany:
    def __init__(self, repository: CompanyRepository) -> None:
        self._repository = repository

    def execute(self, company_id: int) -> CompanyDTO | None:
        return self._repository.get(company_id)


class UpdateCompany:
    def __init__(self, repository: CompanyRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateCompanyCommand) -> CompanyDTO:
        if "base_currency" in command.fields and command.base_currency:
            command = UpdateCompanyCommand(
                company_id=command.company_id,
                fields=command.fields,
                name=command.name,
                legal_name=command.legal_name,
                registration_no=command.registration_no,
                tax_no=command.tax_no,
                base_currency=command.base_currency.upper(),
                address=command.address,
                is_active=command.is_active,
            )
        return self._repository.update(command)


class ListCompanies:
    def __init__(self, repository: CompanyRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> CompanyPageDTO:
        if user_id is None:
            items = self._repository.list_all(skip=skip, limit=limit)
            total = self._repository.count_all()
        else:
            items = self._repository.list_for_user(user_id=user_id, skip=skip, limit=limit)
            total = self._repository.count_for_user(user_id=user_id)
        return CompanyPageDTO(items=tuple(items), total=total, skip=skip, limit=limit)
