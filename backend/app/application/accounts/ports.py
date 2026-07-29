"""Application ports for account persistence."""

from typing import Protocol

from app.application.accounts.dto import AccountDTO, CreateAccountCommand


class AccountRepository(Protocol):
    def create(self, command: CreateAccountCommand) -> AccountDTO:
        ...

    def get_by_id(self, account_id: int) -> AccountDTO | None:
        ...

    def list_by_company(
        self,
        company_id: int,
        skip: int,
        limit: int,
    ) -> list[AccountDTO]:
        ...

    def count_by_company(self, company_id: int) -> int:
        ...
