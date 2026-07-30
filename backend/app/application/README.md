# Application Layer

Purpose: coordinate use cases around domain policy and abstract repository
ports.

Contains accounting commands, queries, use cases, DTOs, and repository ports.
It must not import FastAPI, SQLAlchemy sessions or ORM models, accounting API
schemas, or AI provider SDKs. It must not mutate database sessions; transaction
ownership remains at the route boundary.

Status: active for Accounts, Fiscal, Journals, Reports, and AI/Gemini
accounting access. Static rules are enforced by
`backend/tests/test_architecture_guards.py`.
