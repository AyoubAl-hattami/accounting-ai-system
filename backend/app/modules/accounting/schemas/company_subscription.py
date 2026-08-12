from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SubscriptionStatus = Literal["trial", "active", "past_due", "suspended", "cancelled"]


class SubscriptionRead(BaseModel):
    company_id: int
    status: SubscriptionStatus
    id: int | None = None
    plan_code: str | None = None
    expires_at: datetime | None = None
    trial_ends_at: datetime | None = None
    suspended_at: datetime | None = None
    cancelled_at: datetime | None = None
    suspension_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CompanySubscriptionRead(BaseModel):
    """Platform admin view of one tenant and its subscription."""

    company_id: int
    company_name: str
    base_currency: str
    company_is_active: bool
    subscription: SubscriptionRead
    effective_status: SubscriptionStatus
    days_remaining: int | None = None
    member_count: int = 0
    created_at: datetime | None = None
    primary_admin_email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PlatformDashboardRead(BaseModel):
    total_clients: int
    trial_subscriptions: int
    active_subscriptions: int
    past_due_subscriptions: int
    suspended_subscriptions: int
    cancelled_subscriptions: int
    recent_clients: list[CompanySubscriptionRead]

    model_config = ConfigDict(from_attributes=True)


class SubscriptionUpdate(BaseModel):
    status: SubscriptionStatus | None = None
    plan_code: str | None = Field(default=None, max_length=50)
    expires_at: datetime | None = None
    suspension_reason: str | None = None


class SubscriptionExtend(BaseModel):
    period: Literal["month", "year"] = "month"


class SubscriptionActivate(BaseModel):
    expires_at: datetime | None = None
    plan_code: str | None = Field(default=None, max_length=50)


class SubscriptionSuspend(BaseModel):
    reason: str | None = None


class SubscriptionCancel(BaseModel):
    reason: str | None = None


class CompanySubscriptionStatusRead(BaseModel):
    """Company-facing projection: enough to explain a lockout, nothing more."""

    company_id: int
    effective_status: SubscriptionStatus
    expires_at: datetime | None = None
    days_remaining: int | None = None
    is_active: bool
