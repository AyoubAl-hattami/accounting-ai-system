from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.accounting.schemas.audit import AuditLogRead
from app.modules.accounting.services.audit_service import list_audit_logs


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


@router.get(
    "",
    response_model=list[AuditLogRead],
)
def list_audit_logs_endpoint(
    company_id: int | None = Query(default=None, ge=1),
    entity_type: str | None = Query(default=None),
    entity_id: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_audit_logs(
        db=db,
        company_id=company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        skip=skip,
        limit=limit,
    )