# Transaction Boundaries

## Ratified ownership rule (Phase 29)

**Routes own the final transaction commit.**  No unit-of-work port will be
introduced.

```text
FastAPI route
  -> assembles repositories and use cases
  -> invokes application use case (coordinates business logic, no commit)
       -> repositories stage changes (flush for identifiers; no commit)
       -> audit helper stages required audit event
  -> route commits (or rolls back) once
```

Application use cases orchestrate business logic and coordinate repositories.
They do not own or call `commit()`.  The route is the single commit point.

## Layer responsibilities

### Routes

Routes:

- Authenticate requests and extract actor context.
- Enforce company access and RBAC.
- Convert Pydantic payloads to application commands.
- Invoke the primary application use case.
- Write required audit records via `audit_service`.
- Call `db.commit()` once after all business and audit work is staged.
- Translate domain/application errors into stable HTTP responses and serialize
  results.

Routes are the composition root and the transaction owner.

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

- Define the mutation boundary in business terms.
- Coordinate authorization inputs, repositories, domain policy, and audit
  events.
- Return a stable result DTO or raise a domain/application error.
- Must not import FastAPI, SQLAlchemy sessions, Pydantic API schemas, or
  external AI SDKs.
- Must not call `commit()`, `flush()`, `add()`, or `delete()` on a database
  session.

Committing is the route's responsibility, not the use case's.

## Required audit atomicity

For business operations requiring an audit record:

```text
business mutation + required audit record = one transaction
```

Because the route owns `commit()`, it is responsible for ensuring both the
business mutation and the required audit record are staged before committing.
If the audit record cannot be persisted, the route must not commit.  If the
business mutation fails, no success audit record may remain.

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

A flush is not a successful business transaction.  API success must only be
returned after the route commits.

When a flush fails, the route must roll back before the session is reused.
Infrastructure exceptions should be translated to stable application errors at
the repository or use-case boundary.

## Read-only operations

Queries do not require an explicit business commit.  Report and listing use
cases should use read-oriented repository or report-reader ports.  They must
still respect company scope, authorization, and a consistent view appropriate
to the request.

## Migration guidance

Existing service and audit helpers may contain internal commits.  The migration
strategy is:

1. Inventory every service mutation and every caller.
2. Record whether it currently commits, flushes, refreshes, or rolls back.
3. Add focused atomicity tests for success and failure.
4. Migrate one endpoint/use case at a time.
5. Move the commit point to the route.
6. Remove internal commits from helpers only when the route fully controls the
   transaction.
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
