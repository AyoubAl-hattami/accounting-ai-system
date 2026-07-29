# API Interface

Purpose: adapt HTTP requests and responses to application use cases.

May later contain FastAPI routes, Pydantic schemas, dependencies, serialization,
and error translation. It must not implement journal/report rules, concrete
repositories, provider fallback, or commit transactions.

Status: scaffolding only. Existing API behavior remains under
`backend/app/modules/accounting` until migrated safely.
