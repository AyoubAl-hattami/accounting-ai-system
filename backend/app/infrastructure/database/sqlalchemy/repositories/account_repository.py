"""SQLAlchemy implementation of the account repository port."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.accounts.dto import (
    AccountDTO,
    CreateAccountCommand,
    SeedDefaultAccountsCommand,
    SeedDefaultAccountsResultDTO,
    UpdateAccountCommand,
)
from app.application.accounts.ports import AccountRepository
from app.core.database import flush_or_rollback
from app.modules.accounting.models.account import Account


class SqlAlchemyAccountRepository(AccountRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _to_dto(account: Account) -> AccountDTO:
        return AccountDTO(
            id=account.id,
            company_id=account.company_id,
            code=account.code,
            name=account.name,
            account_type=account.account_type,
            parent_id=account.parent_id,
            description=account.description,
            is_active=account.is_active,
            is_system=account.is_system,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )

    def create(self, command: CreateAccountCommand) -> AccountDTO:
        account = Account(
            company_id=command.company_id,
            code=command.code,
            name=command.name,
            account_type=command.account_type,
            parent_id=command.parent_id,
            description=command.description,
            is_active=command.is_active,
            is_system=command.is_system,
        )
        self._db.add(account)
        flush_or_rollback(self._db)
        return self._to_dto(account)

    def update(self, command: UpdateAccountCommand) -> AccountDTO:
        statement = select(Account).where(Account.id == command.account_id)
        account = self._db.scalar(statement)
        if account is None:
            raise RuntimeError(f"Account {command.account_id} disappeared before update staging")
        for field in command.fields:
            setattr(account, field, getattr(command, field))
        self._db.add(account)
        flush_or_rollback(self._db)
        return self._to_dto(account)

    def seed_defaults(
        self,
        command: SeedDefaultAccountsCommand,
    ) -> SeedDefaultAccountsResultDTO:
        created_accounts: list[AccountDTO] = []
        skipped_count = 0
        account_by_code: dict[str, AccountDTO] = {}

        for account_def in command.accounts:
            statement = select(Account).where(
                Account.company_id == command.company_id,
                Account.code == account_def.code,
            )
            existing_account = self._db.scalar(statement)

            if existing_account is not None:
                account_by_code[account_def.code] = self._to_dto(existing_account)
                skipped_count += 1
                continue

            parent_id = None
            if account_def.parent_code:
                parent = account_by_code.get(account_def.parent_code)
                if parent is None:
                    parent_statement = select(Account).where(
                        Account.company_id == command.company_id,
                        Account.code == account_def.parent_code,
                    )
                    parent_account = self._db.scalar(parent_statement)
                    if parent_account is not None:
                        parent = self._to_dto(parent_account)
                if parent is not None:
                    parent_id = parent.id

            account = Account(
                company_id=command.company_id,
                code=account_def.code,
                name=account_def.name,
                account_type=account_def.account_type,
                parent_id=parent_id,
                description=account_def.description,
                is_active=True,
                is_system=account_def.is_system,
            )
            self._db.add(account)
            flush_or_rollback(self._db)
            account_dto = self._to_dto(account)
            account_by_code[account_def.code] = account_dto
            created_accounts.append(account_dto)

        return SeedDefaultAccountsResultDTO(
            company_id=command.company_id,
            created_count=len(created_accounts),
            skipped_count=skipped_count,
            message="Default chart of accounts seeded successfully",
            accounts=created_accounts,
        )
    def get_by_id(self, account_id: int) -> AccountDTO | None:
        statement = select(Account).where(Account.id == account_id)
        account = self._db.scalar(statement)
        return self._to_dto(account) if account is not None else None

    def list_by_company(
        self,
        company_id: int,
        skip: int,
        limit: int,
    ) -> list[AccountDTO]:
        statement = (
            select(Account)
            .where(Account.company_id == company_id)
            .order_by(Account.code.asc())
            .offset(skip)
            .limit(limit)
        )
        accounts = self._db.scalars(statement).all()
        return [self._to_dto(account) for account in accounts]

    def count_by_company(self, company_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(Account)
            .where(Account.company_id == company_id)
        )
        return int(self._db.scalar(statement) or 0)
