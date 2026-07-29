# Domain Layer

Purpose: hold framework-independent business concepts and policies.

May later contain accounting entities, value objects, domain services, policies,
events, and domain errors. It must not contain FastAPI, Pydantic API schemas,
SQLAlchemy, sessions, commits, provider SDKs, or transport concerns.

Status: scaffolding only; no runtime code exists here. Existing behavior remains
under `backend/app/modules/accounting` until migrated safely.
