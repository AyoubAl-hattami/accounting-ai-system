# Backend Target Architecture

## Target structure

```text
backend/app/
  domain/
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
        models/
        repositories/
        mappers/
        unit_of_work.py
    ai/
      rules/
      gemini/
      openai/
    security/
    audit/
    exports/

  interfaces/
    api/
      routes/
      schemas/
      dependencies/
      error_handlers.py

  core/
    config.py
    clock.py
    logging.py
```

This structure should emerge incrementally. Existing
`modules/accounting/{models,routes,schemas,services}` files remain in place until
their callers have migrated and behavioral parity is demonstrated.

## Domain

The domain represents accounting and business policy without FastAPI,
SQLAlchemy, Pydantic API schemas, or AI SDKs.

Project-specific domain responsibilities include:

- Journal balance and line amount invariants.
- Draft, reviewed, posted, reversed, and void transition rules.
- Posted-entry immutability and reversal policy.
- Fiscal-year and open-period eligibility.
- Opening-balance policy.
- Account eligibility and accounting classification.
- Company membership and invitation lifecycle policies where they are not merely
  persistence constraints.
- Normalized identity values such as email.
- Framework-neutral domain errors and audit-event descriptions.

Domain services should be used only for rules spanning multiple entities or
value objects. They must not become a replacement miscellaneous service layer.

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

1. Receive authenticated actor and company context from the interface.
2. Apply application authorization policy.
3. Load data through repository ports.
4. Invoke domain policies.
5. Persist through repositories.
6. Register the required audit record.
7. Commit once through the unit of work.
8. Return a stable result DTO or raise a domain/application error.

## Infrastructure

Infrastructure contains replaceable technical implementations:

- Existing SQLAlchemy models and relationship mappings.
- PostgreSQL repository adapters and row-locking behavior.
- The concrete SQLAlchemy unit of work.
- Gemini and OpenAI SDK clients.
- Deterministic rules-provider adapter.
- Password hashing, token implementations, and external security mechanisms.
- Audit-log persistence.
- CSV and PDF report exporters.
- Concrete clocks or external services when required.

Infrastructure implements application ports; application code must not import
the concrete classes.

## Interfaces/API

The API layer owns:

- FastAPI routers and dependencies.
- Authentication context extraction.
- Pydantic request/response schemas.
- Query/path/header parsing.
- Application command construction.
- Domain/application error to HTTP response mapping.
- Stable API serialization.

Routes should be thin. A route should not independently implement journal
balance checks, legal transitions, report formulas, provider fallback, or
transaction commits.

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
6. Introduce separate domain entities only where rich behavior justifies their
   mapping cost, especially journal aggregates and fiscal policy.

Alembic must continue to import infrastructure persistence metadata. Moving a
Python model is not permission to rewrite migration history.

## Pydantic schema strategy

Pydantic models remain API contracts:

- Transport shape, required fields, size limits, and serialization stay in API
  schemas.
- API schemas are translated to application command/query DTOs.
- Business eligibility and lifecycle decisions move to domain/application code.
- Identity normalization should use a shared value object or policy rather than
  being reimplemented by every route or schema.
- Response schemas must preserve existing field names and formats throughout the
  migration.

## Transaction strategy

Application use cases own transaction boundaries through a unit of work.
Routes, domain objects, and repositories do not commit. Repositories may flush
when an identifier or database constraint result is required.

The transition must start by mapping every current commit/flush caller.
Changing transaction ownership without changing all callers atomically is a
high-risk operation, particularly for journal, invitation, user administration,
and audit flows.

See [Transaction Boundaries](transaction-boundaries.md).

## Audit logging strategy

Required audit events are part of a business mutation:

- The use case describes the audit event.
- The audit repository stages it in the same unit of work.
- Business data and audit data commit together.
- Failure to persist a required audit record rolls back the mutation.

Operational telemetry and application logs are separate and need not share the
business transaction.

Existing atomicity must be preserved while responsibility moves away from route
helpers.

## Report calculation strategy

The former report service combined SQL and accounting semantics. The migrated
report slice now uses:

- Application report queries for authorization and requested scope.
- Report-reader ports returning defined projections.
- SQLAlchemy readers using optimized SQL for ledger-scale aggregation.
- Pure calculators/classifiers for testable accounting rules where practical.
- Separate API, CSV, and PDF presenters.

SQL aggregation is not an architectural failure. It becomes a problem only when
database mechanics, business meaning, permissions, and presentation cannot be
tested or changed independently.

## AI provider strategy

Application ports should describe capabilities, not vendors:

- `JournalSuggestionProvider`
- `IntentClassifier`
- `AccountingAnswerGenerator`

Gemini, OpenAI, and rules implementations belong in infrastructure. Prompt
construction, SDK calls, provider parsing, and provider-specific validation
remain with adapters. Grounding, permission checks, company scoping, and
confirmed mutations remain in application.

The current provider base and deterministic fallback are foundations to retain,
but the large Gemini assistant service should be decomposed behind its current
API facade rather than rewritten wholesale.

## High-risk areas retained after migration

- Journal routes and the SQLAlchemy journal repository.
- Report routes, report use cases, and the read-only report repository.
- `gemini_assistant_service.py`
- `ai_routes.py`
- `audit_service.py`
- Any route that currently owns a final commit or rollback.
- Alembic metadata imports

These areas require focused compatibility and atomicity verification before
future changes.
