"""SQLAlchemy-backed audit persistence adapter.

Implements ``AuditWriter`` and ``AuditReader`` from
``application.audit.ports``.  Directly uses the ``AuditLog`` ORM model and
SQLAlchemy session — no accounting-service dependency.

Phase-45 note: ``audit_service`` helpers have been inlined here so that the
infrastructure layer no longer imports from ``app.modules.accounting.services``.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.audit.dto import AuditLogDTO, AuditWriteCommand
from app.modules.accounting.models.audit_log import AuditLog


def _to_dto(audit_log: AuditLog) -> AuditLogDTO:
    return AuditLogDTO(
        id=audit_log.id,
        action=audit_log.action,
        entity_type=audit_log.entity_type,
        created_at=audit_log.created_at,
        entity_id=audit_log.entity_id,
        company_id=audit_log.company_id,
        actor=audit_log.actor,
        actor_user_id=audit_log.actor_user_id,
        actor_email=audit_log.actor_email,
        actor_name=audit_log.actor_name,
        old_values=audit_log.old_values,
        new_values=audit_log.new_values,
        ip_address=audit_log.ip_address,
        user_agent=audit_log.user_agent,
        description=audit_log.description,
    )


class SQLAlchemyAuditWriter:
    """Flush-only audit writer.  Routes commit after staging."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def stage(self, command: AuditWriteCommand) -> AuditLogDTO:
        """Stage the audit record in the current transaction without committing."""
        audit_log = AuditLog(
            company_id=command.company_id,
            actor=command.actor,
            actor_user_id=command.actor_user_id,
            actor_email=command.actor_email,
            actor_name=command.actor_name,
            action=command.action,
            entity_type=command.entity_type,
            entity_id=command.entity_id,
            old_values=command.old_values,
            new_values=command.new_values,
            ip_address=command.ip_address,
            user_agent=command.user_agent,
            description=command.description,
        )
        self._db.add(audit_log)
        try:
            self._db.flush()
        except Exception:
            self._db.rollback()
            raise
        return _to_dto(audit_log)


class SQLAlchemyAuditReader:
    """Read-only audit reader."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list(
        self,
        *,
        company_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        action: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLogDTO]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        if company_id is not None:
            stmt = stmt.where(AuditLog.company_id == company_id)
        if entity_type is not None:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        stmt = stmt.offset(skip).limit(limit)
        return [_to_dto(log) for log in self._db.scalars(stmt).all()]

    def count(
        self,
        *,
        company_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        action: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(AuditLog)
        if company_id is not None:
            stmt = stmt.where(AuditLog.company_id == company_id)
        if entity_type is not None:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        return int(self._db.scalar(stmt) or 0)
