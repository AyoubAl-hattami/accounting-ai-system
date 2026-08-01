"""Audit application data transfer objects.

These DTOs are framework-neutral.  They must not import FastAPI, SQLAlchemy,
or any concrete infrastructure adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AuditWriteCommand:
    """Command describing an audit event to be staged within the current
    caller-owned transaction.  The caller (route) commits after staging.
    """

    action: str
    entity_type: str
    entity_id: int | None = None
    company_id: int | None = None
    actor: str = "system"
    actor_user_id: int | None = None
    actor_email: str | None = None
    actor_name: str | None = None
    old_values: dict | None = None
    new_values: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class AuditLogDTO:
    """Read projection of a persisted audit log record."""

    id: int
    action: str
    entity_type: str
    created_at: datetime
    entity_id: int | None = None
    company_id: int | None = None
    actor: str = "system"
    actor_user_id: int | None = None
    actor_email: str | None = None
    actor_name: str | None = None
    old_values: dict | None = None
    new_values: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    description: str | None = None
