# Application Layer

Purpose: coordinate use cases around domain policy and abstract ports.

May later contain commands, queries, use cases, DTOs, repository ports, and
unit-of-work ports. It must not contain FastAPI responses, concrete SQLAlchemy
repositories, provider SDKs, or direct commits outside an application unit of
work.

Status: scaffolding only. Existing services and routes remain in
`backend/app/modules/accounting`.
