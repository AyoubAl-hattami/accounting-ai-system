"""SQLAlchemy implementation of the account repository port."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.accounts.dto import (
    AccountDTO,
    CreateAccountCommand,
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
