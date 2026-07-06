from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.core.pagination import PaginatedResponse
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.audit import AuditLogRead
from app.modules.accounting.services.audit_service import (
    count_audit_logs,
    list_audit_logs,
)


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogRead],
)
def list_audit_logs_endpoint(
    company_id: int = Query(..., ge=1),
    entity_type: str | None = Query(default=None),
    entity_id: int | None = Query(default=None, ge=1),
    action: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
        allowed_roles={"admin", "auditor"},
    )

    audit_logs = list_audit_logs(
        db=db,
        company_id=company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        skip=skip,
        limit=limit,
    )

    total = count_audit_logs(
        db=db,
        company_id=company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
    )

    return PaginatedResponse[AuditLogRead](
        items=audit_logs,
        total=total,
        skip=skip,
        limit=limit,
    )