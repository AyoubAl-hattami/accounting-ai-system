from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import flush_or_rollback
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.company import Company
from app.modules.accounting.schemas.account import AccountCreate, AccountUpdate


def get_company_or_none(db: Session, company_id: int) -> Company | None:
    statement = select(Company).where(Company.id == company_id)
    return db.scalar(statement)


def get_account(db: Session, account_id: int) -> Account | None:
    statement = select(Account).where(Account.id == account_id)
    return db.scalar(statement)


def get_account_by_code(
    db: Session,
    company_id: int,
    code: str,
) -> Account | None:
    statement = select(Account).where(
        Account.company_id == company_id,
        Account.code == code,
    )
    return db.scalar(statement)


def list_accounts(
    db: Session,
    company_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Account]:
    statement = select(Account).order_by(Account.code.asc())

    if company_id is not None:
        statement = statement.where(Account.company_id == company_id)

    statement = statement.offset(skip).limit(limit)

    return list(db.scalars(statement).all())
def count_accounts(
    db: Session,
    company_id: int | None = None,
) -> int:
    statement = select(func.count()).select_from(Account)

    if company_id is not None:
        statement = statement.where(Account.company_id == company_id)

    return int(db.scalar(statement) or 0)


def create_account(db: Session, payload: AccountCreate) -> Account:
    account = Account(
        company_id=payload.company_id,
        code=payload.code.strip(),
        name=payload.name.strip(),
        account_type=payload.account_type,
        parent_id=payload.parent_id,
        description=payload.description,
        is_active=payload.is_active,
        is_system=payload.is_system,
    )

    db.add(account)
    flush_or_rollback(db)

    return account


def update_account(
    db: Session,
    account: Account,
    payload: AccountUpdate,
) -> Account:
    update_data = payload.model_dump(exclude_unset=True)

    if "code" in update_data and update_data["code"]:
        update_data["code"] = update_data["code"].strip()

    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()

    for field, value in update_data.items():
        setattr(account, field, value)

    db.add(account)
    flush_or_rollback(db)

    return account
