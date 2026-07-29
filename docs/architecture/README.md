# Architecture Direction

This directory records the target Clean Architecture direction for the
Accounting AI System. It is a migration guide, not a description of a completed
refactor.

The system already has valuable boundaries: FastAPI routes and Pydantic schemas
are separated, accounting features have named services, AI providers have a
common abstraction, and the React application is grouped by feature. The next
step is to make dependency direction and responsibility ownership explicit
without disrupting working behavior.

The migration must be incremental. Existing endpoints, database mappings,
accounting results, permissions, audit guarantees, assistant safeguards, route
URLs, and Arabic/RTL behavior are compatibility constraints. New boundaries
should first wrap existing implementations; old paths should be removed only
after behavioral parity has been demonstrated.

## Documents

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
