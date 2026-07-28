from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.accounting.models.audit_log import AuditLog


def create_audit_log(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    company_id: int | None = None,
    actor: str = "system",
    actor_user_id: int | None = None,
    actor_email: str | None = None,
    actor_name: str | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    description: str | None = None,
    commit: bool = True,
) -> AuditLog:
    audit_log = AuditLog(
        company_id=company_id,
        actor=actor,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        actor_name=actor_name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent,
        description=description,
    )

    db.add(audit_log)
    if commit:
        db.commit()
        db.refresh(audit_log)
    else:
        try:
            db.flush()
        except Exception:
            db.rollback()
            raise

    return audit_log


def create_atomic_audit_log(db: Session, **audit_values) -> AuditLog:
    """Commit a pending mutation and its audit row as one transaction."""
    try:
        audit_log = create_audit_log(db=db, commit=False, **audit_values)
        db.commit()
        return audit_log
    except Exception:
        db.rollback()
        raise


def prepare_audit_log(db: Session, **audit_values) -> AuditLog:
    '''Flush an audit row without committing the caller-owned transaction.'''
    return create_audit_log(db=db, commit=False, **audit_values)


def list_audit_logs(
    db: Session,
    company_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: str | None = None,
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

    if action is not None:
        statement = statement.where(AuditLog.action == action)

    statement = statement.offset(skip).limit(limit)

    return list(db.scalars(statement).all())


def count_audit_logs(
    db: Session,
    company_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: str | None = None,
) -> int:
    statement = select(func.count()).select_from(AuditLog)

    if company_id is not None:
        statement = statement.where(AuditLog.company_id == company_id)

    if entity_type is not None:
        statement = statement.where(AuditLog.entity_type == entity_type)

    if entity_id is not None:
        statement = statement.where(AuditLog.entity_id == entity_id)

    if action is not None:
        statement = statement.where(AuditLog.action == action)

    return int(db.scalar(statement) or 0)
