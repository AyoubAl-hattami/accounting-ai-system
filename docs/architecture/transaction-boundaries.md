# Transaction Boundaries

## Ownership rule

An application mutation use case owns one unit-of-work boundary.

```text
FastAPI route
  -> application use case
       -> repositories stage business changes
       -> audit repository stages required audit event
       -> unit of work commits once
```

Routes, domain code, and repositories do not commit.

## Layer responsibilities

### Routes

Routes:

- Obtain authentication, company, and request context.
- Convert a Pydantic payload to an application command.
- Invoke a use case.
- Translate errors and serialize results.

Routes must not call `commit()` or decide whether a business mutation and its
audit record should share a transaction.

### Domain

Domain entities and policies:

- Validate accounting invariants.
- Produce state transitions or domain errors.
- May describe domain events.

They have no database session and never flush, commit, or roll back.

### Repositories

Repositories:

- Load and stage aggregates or persistence records.
- Apply database-specific locking inside infrastructure adapters.
- May call `flush()` when a generated identifier, constraint result, or
  persistence synchronization is required.
- Do not call `commit()`.
- Do not silently recover from a failed flush and continue the same mutation.

### Application use cases

Application use cases:

- Define the mutation boundary.
- Coordinate authorization, repositories, domain policy, and audit events.
- Commit through a unit-of-work port after all required work is staged.
- Roll back the complete transaction on any failure.

The concrete unit of work owns the SQLAlchemy session lifecycle and implements
commit and rollback behavior.

## Required audit atomicity

For business operations requiring an audit record:

```text
business mutation + required audit record = one transaction
```

If the audit record cannot be persisted, the business mutation must not commit.
If the business mutation fails, no success audit record may remain.

This applies especially to:

- Account and company changes.
- Company membership and invitation lifecycle operations.
- Global user activation/deactivation.
- Fiscal configuration changes.
- Journal create, review, post, reverse, and void operations.
- Confirmed AI-assisted journal actions.

Application telemetry, diagnostics, and external logging are not substitutes for
the required audit record and may use different delivery guarantees.

## Flush policy

A repository may flush to:

- Obtain a generated primary key or journal identifier.
- Surface a unique or foreign-key violation before creating dependent records.
- Synchronize a relationship required later in the same transaction.

A flush is not a successful business transaction. API success must only be
returned after the unit of work commits.

When a flush fails, the unit of work must roll back before the session is reused.
Infrastructure exceptions should be translated to stable application errors at
the repository or use-case boundary.

## Read-only operations

Queries do not require an explicit business commit. Report and listing use cases
should use read-oriented repository or report-reader ports. They must still
respect company scope, authorization, and a consistent view appropriate to the
request.

## Migration from the current design

Current code includes commits, flushes, and rollbacks across service and audit
helpers, with routes participating in transaction completion. Migration must be
caller-driven:

1. Inventory every service mutation and every caller.
2. Record whether it currently commits, flushes, refreshes, or rolls back.
3. Add focused atomicity tests for success and failure.
4. Introduce a unit-of-work wrapper over the existing SQLAlchemy session.
5. Migrate one endpoint/use case at a time.
6. Remove the old commit only when every caller uses the new boundary.
7. Keep business mutation and required audit persistence in the same migration
   slice.

Do not globally replace `commit()` with `flush()` or vice versa.

## Required verification

Transaction-focused verification should cover:

- Successful mutation and audit commit together.
- Business failure leaves neither mutation nor success audit.
- Audit failure rolls back the business mutation.
- Flush constraint failure leaves the session recoverable after rollback.
- Returned objects contain generated fields required by the API.
- Nested service calls do not commit early.
- Concurrent journal/invitation operations preserve uniqueness and lifecycle
  guarantees.
- Existing API status and error contracts remain stable.

## Compatibility guarantees

Transaction refactoring must not change accounting results, journal lifecycle,
database schema, Alembic history, RBAC/company isolation, audit atomicity, or AI
confirmation safety.
