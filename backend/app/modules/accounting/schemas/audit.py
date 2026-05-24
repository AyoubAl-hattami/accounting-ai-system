from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    id: int

    company_id: int | None = None
    actor: str

    action: str
    entity_type: str
    entity_id: int | None = None

    description: str | None = None

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)