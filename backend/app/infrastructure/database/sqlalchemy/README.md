# SQLAlchemy Infrastructure

Purpose: hold concrete SQLAlchemy persistence adapters.

May later contain persistence models, session-backed repositories, mappings, and
the SQLAlchemy unit of work. It must not contain API schemas, HTTP errors,
provider SDKs, or independent business-policy decisions.

Status: scaffolding only. Existing ORM models remain under
`backend/app/modules/accounting/models`.
