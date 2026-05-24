from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.accounting.models.audit_log import AuditLog


def create_audit_log(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    company_id: int | None = None,
    actor: str = "system",
    description: str | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        company_id=company_id,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )

    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)

    return audit_log


def list_audit_logs(
    db: Session,
    company_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AuditLog]:
    statement = select(AuditLog).order_by(AuditLog.created_at.desc())

    if company_id is not None:
        statement = statement.where(AuditLog.company_id == company_id)

    if entity_type is not None:
        statement = statement.where(AuditLog.entity_type == entity_type)

    if entity_id is not None:
        statement = statement.where(AuditLog.entity_id == entity_id)

    statement = statement.offset(skip).limit(limit)

    return list(db.scalars(statement).all())