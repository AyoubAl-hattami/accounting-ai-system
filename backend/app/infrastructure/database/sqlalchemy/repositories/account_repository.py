"""SQLAlchemy implementation of the account repository port."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.accounts.dto import AccountDTO
from app.application.accounts.ports import AccountRepository
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
