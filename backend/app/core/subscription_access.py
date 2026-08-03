"""Tenant-level subscription gate for company business APIs.

The check lives here rather than in each router so that ``ensure_company_access``
— the one dependency every company-scoped endpoint already calls — is the single
place a lapsed tenant can be turned away.
"""

from fastapi import HTTPException, status

from app.application.subscriptions.policy import effective_status, grants_access
from app.infrastructure.database.sqlalchemy.repositories.subscription_repository import (
    SqlAlchemySubscriptionRepository,
)

SUBSCRIPTION_INACTIVE_CODE = "SUBSCRIPTION_INACTIVE"
SUBSCRIPTION_INACTIVE_MESSAGE = "Company subscription is inactive or expired."


def ensure_active_subscription(db, company_id: int) -> None:
    """Raise 403 SUBSCRIPTION_INACTIVE unless the company may transact."""
    subscription = SqlAlchemySubscriptionRepository(db).get(company_id)

    if subscription is None:
        # No row yet means the company predates subscription management or was
        # created outside the API.  Blocking it would lock out working tenants,
        # so it is treated as unmanaged until a platform admin acts on it.
        return

    if grants_access(subscription.status, subscription.expires_at):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": SUBSCRIPTION_INACTIVE_CODE,
            "message": SUBSCRIPTION_INACTIVE_MESSAGE,
            "status": effective_status(subscription.status, subscription.expires_at),
        },
    )
