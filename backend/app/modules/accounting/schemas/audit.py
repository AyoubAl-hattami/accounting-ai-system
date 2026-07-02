from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    id: int

    company_id: int | None = None
    actor: str
    actor_user_id: int | None = None
    actor_email: str | None = None
    actor_name: str | None = None

    action: str
    entity_type: str
    entity_id: int | None = None

    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    description: str | None = None

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)