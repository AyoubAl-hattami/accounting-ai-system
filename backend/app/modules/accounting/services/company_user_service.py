from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.company_user import (
    CompanyUserCreate,
    CompanyUserUpdate,
)


def get_company(db: Session, company_id: int) -> Company | None:
    statement = select(Company).where(Company.id == company_id)
    return db.scalar(statement)


def get_user(db: Session, user_id: int) -> User | None:
    statement = select(User).where(User.id == user_id)
    return db.scalar(statement)


def get_company_user(
    db: Session,
    company_user_id: int,
) -> CompanyUser | None:
    statement = select(CompanyUser).where(CompanyUser.id == company_user_id)
    return db.scalar(statement)


def get_company_user_by_company_and_user(
    db: Session,
    company_id: int,
    user_id: int,
) -> CompanyUser | None:
    statement = select(CompanyUser).where(
        CompanyUser.company_id == company_id,
        CompanyUser.user_id == user_id,
    )
    return db.scalar(statement)


def list_company_users(
    db: Session,
    company_id: int | None = None,
    user_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[CompanyUser]:
    statement = select(CompanyUser).order_by(CompanyUser.id.asc())

    if company_id is not None:
        statement = statement.where(CompanyUser.company_id == company_id)

    if user_id is not None:
        statement = statement.where(CompanyUser.user_id == user_id)

    statement = statement.offset(skip).limit(limit)

    return list(db.scalars(statement).all())


def create_company_user(
    db: Session,
    payload: CompanyUserCreate,
) -> CompanyUser:
    company_user = CompanyUser(
        company_id=payload.company_id,
        user_id=payload.user_id,
        role=payload.role,
        is_active=payload.is_active,
    )

    db.add(company_user)
    db.commit()
    db.refresh(company_user)

    return company_user


def update_company_user(
    db: Session,
    company_user: CompanyUser,
    payload: CompanyUserUpdate,
) -> CompanyUser:
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(company_user, field, value)

    db.add(company_user)
    db.commit()
    db.refresh(company_user)

    return company_user


def user_has_company_access(
    db: Session,
    user_id: int,
    company_id: int,
) -> bool:
    company_user = get_company_user_by_company_and_user(
        db=db,
        company_id=company_id,
        user_id=user_id,
    )

    return bool(company_user and company_user.is_active)