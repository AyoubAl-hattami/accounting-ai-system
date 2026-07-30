# Architecture Direction

This directory records the Clean Architecture direction for the Accounting AI
System. The accounting backend migration is complete for Accounts, Fiscal,
Journals, Reports, and AI/Gemini accounting access; other areas remain
incremental migration candidates.

The migrated backend uses framework-neutral application use cases and ports,
SQLAlchemy repository adapters, and route-owned HTTP, access, audit, and
transaction concerns. Static architecture guards protect these boundaries.

The migration must be incremental. Existing endpoints, database mappings,
accounting results, permissions, audit guarantees, assistant safeguards, route
URLs, and Arabic/RTL behavior are compatibility constraints. New boundaries
should first wrap existing implementations; old paths should be removed only
after behavioral parity has been demonstrated.

## Documents

- [Migration status and manual validation](clean-architecture-migration-status.md)
- [Clean Architecture roadmap](clean-architecture-roadmap.md)
- [Dependency rules](dependency-rules.md)
- [Backend target architecture](backend-target-architecture.md)
- [Frontend target architecture](frontend-target-architecture.md)
- [Transaction boundaries](transaction-boundaries.md)
- [AI architecture](ai-architecture.md)
- [Theme architecture](theme-architecture.md)

## Non-negotiable compatibility constraints

Architecture work must not unintentionally change:

- Public API paths, request/response contracts, status codes, or error behavior.
- PostgreSQL schema, SQLAlchemy mappings, or Alembic revision history.
- Accounting calculations, balances, report totals, or fiscal-date behavior.
- Journal draft, review, post, reverse, and void lifecycle rules.
- Authentication, RBAC, platform privileges, or company isolation.
- Atomic persistence of required audit records with business mutations.
- Explicit confirmation before an AI-suggested mutation.
- Frontend route URLs, localization keys, or Arabic/RTL behavior.

Each migration slice should have a narrow purpose, a dedicated commit, a
behavioral baseline, and a simple rollback path.
