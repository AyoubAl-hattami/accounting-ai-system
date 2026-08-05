from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.password_change_gate import password_change_required_error
from app.core.subscription_access import ensure_active_subscription
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
    *,
    require_active_subscription: bool = True,
) -> CompanyUser:
    """Authorise a company-scoped request.

    Subscription enforcement defaults to on, so every business endpoint that
    already calls this is gated without touching its code.  Endpoints the client
    still needs while locked out — reading its own membership or company profile
    — opt out with ``require_active_subscription=False``.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Already enforced by ``get_current_user``; repeated here because this is the
    # one gate every company-scoped endpoint calls, and it must never be the
    # weaker of the two.  No /auth route reaches this function.
    if current_user.must_change_password:
        raise password_change_required_error()

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

    # Checked after membership so a non-member learns nothing about the tenant's
    # subscription state. A company admin has no bypass here by design.
    if require_active_subscription:
        ensure_active_subscription(db=db, company_id=company_id)

    return company_user
    