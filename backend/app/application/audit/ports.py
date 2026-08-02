"""Audit application ports.

Ports are defined as ``typing.Protocol`` — never ABC — so application code
remains framework-neutral.  Infrastructure adapters implement these protocols
without a formal inheritance relationship.
"""

from __future__ import annotations

from typing import Protocol

from app.application.audit.dto import AuditLogDTO, AuditWriteCommand


class AuditWriter(Protocol):
    """Stages an audit record in the caller-owned transaction.

    The writer must NOT commit.  It may flush to obtain a generated identifier.
    The calling route is responsible for committing after all business and audit
    work is staged.
    """

    def stage(self, command: AuditWriteCommand) -> AuditLogDTO:
        """Persist the audit record in the current transaction without committing."""
        ...


class AuditReader(Protocol):
    """Read-only access to persisted audit records."""

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
        """Return a page of audit records matching the given filters."""
        ...

    def count(
        self,
        *,
        company_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        action: str | None = None,
    ) -> int:
        """Return the total count of audit records matching the given filters."""
        ...
