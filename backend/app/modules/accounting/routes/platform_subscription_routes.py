"""Platform-owner subscription administration.

Every route here is gated on ``get_current_platform_admin``.  The platform owner
is never a member of a client company, so none of these calls go through
``ensure_company_access`` — that is the point of a separate surface.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.application.subscriptions.dto import UpdateSubscriptionCommand
from app.application.subscriptions.policy import VALID_STATUSES
from app.application.subscriptions.use_cases import (
    ActivateSubscription,
    CancelSubscription,
    ExtendSubscription,
    GetCompanySubscription,
    ListCompanySubscriptions,
    SuspendSubscription,
    UpdateSubscription,
)
from app.core.auth_dependencies import get_current_platform_admin
from app.core.database import get_db
from app.core.pagination import PaginatedResponse
from app.infrastructure.database.sqlalchemy.repositories.subscription_repository import (
    SqlAlchemySubscriptionRepository,
)
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.company_subscription import (
    CompanySubscriptionRead,
    SubscriptionActivate,
    SubscriptionCancel,
    SubscriptionExtend,
    SubscriptionSuspend,
    SubscriptionUpdate,
)
from app.modules.accounting.services.audit_service import prepare_audit_log


router = APIRouter(
    prefix="/platform/subscriptions",
    tags=["Platform Subscriptions"],
)


def _summary_or_404(db: Session, company_id: int) -> CompanySubscriptionRead:
    repo = SqlAlchemySubscriptionRepository(db)
    summary = GetCompanySubscription(repo).execute(company_id)

    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    return CompanySubscriptionRead.model_validate(summary)


def _record(
    db: Session,
    admin: User,
    company_id: int,
    action: str,
    description: str,
) -> None:
    prepare_audit_log(
        db=db,
        company_id=company_id,
        actor=admin.email,
        actor_user_id=admin.id,
        actor_email=admin.email,
        actor_name=admin.full_name,
        action=action,
        entity_type="company_subscription",
        entity_id=company_id,
        description=description,
    )


@router.get(
    "",
    response_model=PaginatedResponse[CompanySubscriptionRead],
)
def list_subscriptions_endpoint(
    search: str | None = Query(default=None, max_length=255),
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_platform_admin),
):
    if status_filter is not None and status_filter not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown subscription status '{status_filter}'",
        )

    repo = SqlAlchemySubscriptionRepository(db)
    page = ListCompanySubscriptions(repo).execute(
        search=search, status=status_filter, skip=skip, limit=limit
    )

    return PaginatedResponse[CompanySubscriptionRead](
        items=[CompanySubscriptionRead.model_validate(item) for item in page.items],
        total=page.total,
        skip=page.skip,
        limit=page.limit,
    )


@router.get(
    "/{company_id}",
    response_model=CompanySubscriptionRead,
)
def get_subscription_endpoint(
    company_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_platform_admin),
):
    return _summary_or_404(db, company_id)


@router.patch(
    "/{company_id}",
    response_model=CompanySubscriptionRead,
)
def update_subscription_endpoint(
    company_id: int,
    payload: SubscriptionUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    _summary_or_404(db, company_id)

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No subscription fields supplied",
        )

    repo = SqlAlchemySubscriptionRepository(db)
    UpdateSubscription(repo).execute(
        UpdateSubscriptionCommand(
            company_id=company_id,
            fields=frozenset(update_data.keys()),
            **update_data,
        )
    )

    _record(
        db,
        admin,
        company_id,
        "update_subscription",
        f"Updated subscription fields: {', '.join(sorted(update_data))}",
    )
    db.commit()

    return _summary_or_404(db, company_id)


@router.post(
    "/{company_id}/extend",
    response_model=CompanySubscriptionRead,
)
def extend_subscription_endpoint(
    company_id: int,
    payload: SubscriptionExtend,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    _summary_or_404(db, company_id)

    repo = SqlAlchemySubscriptionRepository(db)
    months = 1 if payload.period == "month" else 0
    years = 1 if payload.period == "year" else 0
    updated = ExtendSubscription(repo).execute(
        company_id, months=months, years=years
    )

    _record(
        db,
        admin,
        company_id,
        "extend_subscription",
        f"Extended subscription by one {payload.period} to {updated.expires_at}",
    )
    db.commit()

    return _summary_or_404(db, company_id)


@router.post(
    "/{company_id}/activate",
    response_model=CompanySubscriptionRead,
)
def activate_subscription_endpoint(
    company_id: int,
    payload: SubscriptionActivate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    _summary_or_404(db, company_id)

    repo = SqlAlchemySubscriptionRepository(db)
    updated = ActivateSubscription(repo).execute(
        company_id, expires_at=payload.expires_at, plan_code=payload.plan_code
    )

    _record(
        db,
        admin,
        company_id,
        "activate_subscription",
        f"Activated subscription, expires {updated.expires_at or 'never'}",
    )
    db.commit()

    return _summary_or_404(db, company_id)


@router.post(
    "/{company_id}/suspend",
    response_model=CompanySubscriptionRead,
)
def suspend_subscription_endpoint(
    company_id: int,
    payload: SubscriptionSuspend,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    _summary_or_404(db, company_id)

    repo = SqlAlchemySubscriptionRepository(db)
    SuspendSubscription(repo).execute(company_id, reason=payload.reason)

    _record(
        db,
        admin,
        company_id,
        "suspend_subscription",
        f"Suspended subscription: {payload.reason or 'no reason given'}",
    )
    db.commit()

    return _summary_or_404(db, company_id)


@router.post(
    "/{company_id}/cancel",
    response_model=CompanySubscriptionRead,
)
def cancel_subscription_endpoint(
    company_id: int,
    payload: SubscriptionCancel,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_platform_admin),
):
    _summary_or_404(db, company_id)

    repo = SqlAlchemySubscriptionRepository(db)
    CancelSubscription(repo).execute(company_id, reason=payload.reason)

    _record(
        db,
        admin,
        company_id,
        "cancel_subscription",
        f"Cancelled subscription: {payload.reason or 'no reason given'}",
    )
    db.commit()

    return _summary_or_404(db, company_id)
