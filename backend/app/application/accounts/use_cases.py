"""Account application use cases."""

from app.application.accounts.dto import (
    AccountDTO,
    AccountPageDTO,
    CreateAccountCommand,
)
from app.application.accounts.ports import AccountRepository


class CreateAccount:
    def __init__(self, repository: AccountRepository) -> None:
        self._repository = repository

    def execute(self, command: CreateAccountCommand) -> AccountDTO:
        normalized_command = CreateAccountCommand(
            company_id=command.company_id,
            code=command.code.strip(),
            name=command.name.strip(),
            account_type=command.account_type,
            parent_id=command.parent_id,
            description=command.description,
            is_active=command.is_active,
            is_system=command.is_system,
        )
        return self._repository.create(normalized_command)


class GetAccount:
    def __init__(self, repository: AccountRepository) -> None:
        self._repository = repository

    def execute(self, account_id: int) -> AccountDTO | None:
        return self._repository.get_by_id(account_id=account_id)


class ListAccounts:
    def __init__(self, repository: AccountRepository) -> None:
        self._repository = repository

    def execute(
        self,
        company_id: int,
        skip: int,
        limit: int,
    ) -> AccountPageDTO:
        items = self._repository.list_by_company(
            company_id=company_id,
            skip=skip,
            limit=limit,
        )
        total = self._repository.count_by_company(company_id=company_id)

        return AccountPageDTO(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
        )
