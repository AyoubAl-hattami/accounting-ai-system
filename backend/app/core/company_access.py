from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.user import User


def get_user_company_role(
    db: Session,
    user_id: int,
    company_id: int,
) -> CompanyUser | None:
    statement = select(CompanyUser).where(
        CompanyUser.user_id == user_id,
        CompanyUser.company_id == company_id,
        CompanyUser.is_active.is_(True),
    )

    return db.scalar(statement)


def ensure_company_access(
    db: Session,
    current_user: User,
    company_id: int,
    allowed_roles: Iterable[str] | None = None,
) -> CompanyUser:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    if current_user.is_superuser:
        return CompanyUser(
            company_id=company_id,
            user_id=current_user.id,
            role="admin",
            is_active=True,
        )

    company_user = get_user_company_role(
        db=db,
        user_id=current_user.id,
        company_id=company_id,
    )

    if not company_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this company",
        )

    if allowed_roles is not None and company_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action",
        )

    return company_user
    