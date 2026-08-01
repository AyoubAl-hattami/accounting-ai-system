# Backend Target Architecture

## Ratified architectural decisions (Phase 29)

1. **Routes own the final transaction commit.**  No unit-of-work port will be
   introduced.  Routes own auth, RBAC, HTTP translation, audit write, and the
   final `db.commit()` / `db.rollback()`.
2. **No directory relocations.**  `routes/`, `models/`, and `schemas/` stay
   under `app/modules/accounting/`.  Boundaries are enforced by import rules
   and guards, not file movement.
3. **Application layer is framework-neutral.**  No FastAPI, SQLAlchemy ORM,
   Pydantic API schemas, infrastructure adapters, or external AI SDKs may be
   imported by application code.
4. **Repositories never commit.**  Repositories may `flush()` when a generated
   identifier or constraint result is required; they do not `commit()`.
5. **Routes are the composition root.**  Routes assemble repositories and use
   cases; inner layers do not locate their own adapters.

## Target structure

```text
backend/app/
  domain/                    ← reserved; currently contains only READMEs
    accounting/
    fiscal/
    identity/
    companies/
    audit/
    ai/

  application/
    accounts/
    journals/
    fiscal/
    reports/
    users/
    companies/
    invitations/
    audit/
    assistant/

  infrastructure/
    database/
      sqlalchemy/
        models/              ← shared with modules/accounting/models (no move)
        repositories/
        mappers/
    ai/
      rules/
      gemini/
      openai/
    security/
    audit/
    exports/

  modules/accounting/        ← stays here; no directory relocation planned
    routes/
    models/
    schemas/
    services/                ← migrated incrementally; deleted when empty

  core/
    config.py
    clock.py
    logging.py
```

`modules/accounting/{routes,models,schemas}` remain in place throughout the
migration.  Only `services/` is scheduled for eventual deletion once all
remaining service consumers are migrated to use cases and infrastructure
adapters.

The `domain/` subtree is reserved for future policy extraction and currently
contains only README placeholder files — no `.py` files.

## Domain

The domain layer is reserved for accounting and business policy without
FastAPI, SQLAlchemy, Pydantic API schemas, or AI SDKs.  It has not been
populated with Python modules; migration toward it is incremental and optional
for simple slices.

Project-specific domain responsibilities include:

- Journal balance and line amount invariants.
- Draft, reviewed, posted, reversed, and void transition rules.
- Posted-entry immutability and reversal policy.
- Fiscal-year and open-period eligibility.
- Opening-balance policy.
- Account eligibility and accounting classification.
- Framework-neutral domain errors and audit-event descriptions.

## Application

The application layer describes what the system does for an actor and company.
It contains commands, queries, use cases, DTOs, and ports.

Examples:

- `CreateAccount`
- `UpdateFiscalPeriod`
- `CreateJournalDraft`
- `ReviewJournalEntry`
- `PostJournalEntry`
- `ReverseJournalEntry`
- `VoidJournalEntry`
- `GenerateTrialBalance`
- `InviteCompanyUser`
- `ConfirmAssistantJournalAction`

A mutation use case should:

1. Receive authenticated actor and company context from the route.
2. Apply application authorization policy.
3. Load data through repository ports.
4. Invoke domain policies.
5. Stage changes through repositories (repositories flush; do not commit).
6. Stage the required audit record.
7. Return a stable result DTO or raise a domain/application error.

The route receives the result and calls `db.commit()` once.

Application code must not import FastAPI, SQLAlchemy sessions, Pydantic API
schemas, external AI SDKs, or concrete infrastructure adapters.

## Infrastructure

Infrastructure contains replaceable technical implementations:

- Existing SQLAlchemy models and relationship mappings.
- PostgreSQL repository adapters and row-locking behavior.
- Gemini and OpenAI SDK clients.
- Deterministic rules-provider adapter.
- Password hashing and token implementations.
- Audit-log persistence.
- CSV and PDF report exporters.
- Concrete clocks or external services when required.

Infrastructure implements application ports; application code must not import
the concrete classes.

## Interfaces/API (routes)

The API layer owns:

- FastAPI routers and dependencies.
- Authentication context extraction.
- Pydantic request/response schemas.
- Query/path/header parsing.
- Application command construction.
- Company access and RBAC enforcement.
- Audit record writes.
- `db.commit()` / `db.rollback()` — the final transaction boundary.
- Domain/application error to HTTP response mapping.
- Stable API serialization.

Routes are deliberately not thin in this design: they own the transaction
boundary by ratified decision.  They should not, however, independently
implement journal balance rules, legal transitions, report formulas, or
provider fallback logic.

## Core

`core` should remain deliberately small:

- Environment/configuration loading.
- Cross-cutting clock and logging abstractions.
- Application composition support.

Company access rules, identity policy, repositories, and accounting helpers
should not be placed in `core` merely because multiple modules use them.

## SQLAlchemy model strategy

Do not replace the current ORM model set in one migration.

1. Keep table names, columns, relationships, constraints, and metadata imports.
2. Treat ORM classes as persistence models.
3. Introduce repository ports around existing queries.
4. Allow transitional adapters to return ORM instances internally if necessary.
5. Extract pure policies from ORM-dependent services.

Alembic must continue to import infrastructure persistence metadata.  Moving a
Python model is not permission to rewrite migration history.

## Pydantic schema strategy

Pydantic models remain API contracts:

- Transport shape, required fields, size limits, and serialization stay in API
  schemas.
- API schemas are translated to application command/query DTOs.
- Business eligibility and lifecycle decisions move to domain/application code.
- Response schemas must preserve existing field names and formats throughout the
  migration.

## Transaction strategy

**Routes own the final transaction commit** by ratified architectural decision.
No unit-of-work port will be introduced.

Application use cases coordinate business logic and stage changes through
repositories.  They do not call `commit()`.  The route commits once after the
use case returns and any required audit record is staged.

Repositories may `flush()` when a generated identifier or database constraint
result is required.  They must not `commit()`.

See [Transaction Boundaries](transaction-boundaries.md).

## Audit logging strategy

Required audit events are part of a business mutation:

- The route or use case describes the audit event.
- The audit helper (`audit_service.create_audit_log`) stages it before the
  route commits.
- Business data and audit data commit together in the route's transaction.
- Failure to persist a required audit record rolls back the mutation.

Operational telemetry and application logs are separate and need not share the
business transaction.

## Report calculation strategy

The report slice uses:

- Application report queries for authorization and requested scope.
- Report-reader ports returning defined projections.
- SQLAlchemy readers using optimized SQL for ledger-scale aggregation.
- Pure calculators/classifiers for testable accounting rules where practical.
- Separate API, CSV, and PDF presenters.

SQL aggregation is not an architectural failure.  It becomes a problem only
when database mechanics, business meaning, permissions, and presentation cannot
be tested or changed independently.

## AI provider strategy

Application ports describe capabilities, not vendors:

- `JournalSuggestionProvider`
- `IntentClassifier`
- `AccountingAnswerGenerator`

Gemini, OpenAI, and rules implementations belong in infrastructure.  Prompt
construction, SDK calls, provider parsing, and provider-specific validation
remain with adapters.  Grounding, permission checks, company scoping, and
confirmed mutations remain in application.

## High-risk areas retained after migration

- Journal routes and the SQLAlchemy journal repository.
- Report routes, report use cases, and the read-only report repository.
- `gemini_assistant_service.py`
- `ai_routes.py`
- `audit_service.py`
- Any route that currently owns a final commit or rollback.
- Alembic metadata imports.

These areas require focused compatibility and atomicity verification before
future changes.
