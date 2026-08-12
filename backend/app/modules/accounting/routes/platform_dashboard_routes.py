"""Platform-owner client and subscription overview."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.application.subscriptions.use_cases import GetPlatformDashboard
from app.core.auth_dependencies import get_current_platform_admin
from app.core.database import get_db
from app.infrastructure.database.sqlalchemy.repositories.subscription_repository import (
    SqlAlchemySubscriptionRepository,
)
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.company_subscription import PlatformDashboardRead


router = APIRouter(prefix="/platform/dashboard", tags=["Platform Dashboard"])


@router.get("", response_model=PlatformDashboardRead)
def get_platform_dashboard_endpoint(
    recent_limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_platform_admin),
):
    summary = GetPlatformDashboard(SqlAlchemySubscriptionRepository(db)).execute(
        recent_limit=recent_limit
    )
    return PlatformDashboardRead.model_validate(summary)
