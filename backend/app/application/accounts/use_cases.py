"""Read-only account application use cases."""

from app.application.accounts.dto import AccountDTO, AccountPageDTO
from app.application.accounts.ports import AccountRepository


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
