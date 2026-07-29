# Companies Domain

Purpose: define company membership and company-scoped business policy.

May later contain membership, role, and company-access invariants. It must not
contain FastAPI dependencies, SQLAlchemy access, route authorization responses,
or global transaction handling.

Status: scaffolding only. Existing company code remains under
`backend/app/modules/accounting`.
