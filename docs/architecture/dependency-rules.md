# Dependency Rules

These rules define intended dependency direction.  They should be adopted
incrementally; existing violations are migration work, not justification for a
single disruptive rewrite.

## Backend dependency direction

```text
interfaces/api (routes) -> application -> domain
                                  ^
                                  |
                           infrastructure
                          implements ports
```

The composition root (routes) instantiates infrastructure adapters and injects
them into application use cases.  Inner layers do not locate their own adapters.

## Domain rules

The domain layer:

- Must not import FastAPI, Starlette, HTTP status codes, or route dependencies.
- Must not import SQLAlchemy, database sessions, ORM query expressions, or
  Alembic.
- Must not import Pydantic API request/response schemas.
- Must not import Gemini, OpenAI, or any other provider SDK.
- Must not import React, frontend concepts, or transport payloads.
- Must not commit, flush, roll back, log HTTP requests, or read global settings.
- May use Python standard-library types and deliberately selected
  framework-neutral libraries.
- Owns accounting invariants and domain errors expressed in accounting language.

Examples suitable for the domain include balanced-entry validation, journal
status-transition policy, fiscal-period eligibility, reversal policy, and
identity value normalization.

## Application rules

The application layer:

- May depend on the domain.
- Defines ports for repositories, clocks, audit persistence, exporters, and AI
  capabilities using `typing.Protocol` (never `ABC`).
- Coordinates use cases, authorization inputs, domain policies, persistence, and
  required audit events.
- Must not depend on concrete SQLAlchemy repositories or AI SDKs.
- Must not raise `HTTPException` or choose HTTP status codes.
- Should use command/query DTOs (`@dataclass(frozen=True, slots=True)`) that do
  not expose provider SDK or API framework types.
- Must not call `commit()`, `flush()`, `add()`, or `delete()` on a database
  session.
- Must not import `app.modules.accounting.services` modules.

Application use cases return result DTOs.  The calling route owns the commit.

## Infrastructure rules

Infrastructure:

- Implements application ports.
- May depend on application port definitions and domain/application DTOs.
- Owns SQLAlchemy mappings, repository implementations, database locking, SDK
  calls, prompt transport, tokens, password hashing, and export libraries.
- Must not contain endpoint authorization policy or decide which user action is
  allowed.
- Must not commit independently; the route owns the final transaction.
- Must not import `app.modules.accounting.services` modules.

## API/interface rules (routes)

FastAPI routes and dependencies:

- Authenticate requests and obtain request-scoped context.
- Parse and validate transport shapes with Pydantic.
- Convert API schemas to application commands and queries.
- Enforce company access (RBAC) before invoking use cases.
- Call one primary application use case.
- Write required audit records via `audit_service`.
- Call `db.commit()` once after all work is staged (routes own the commit).
- Translate domain/application errors into stable HTTP responses.
- Serialize application results.
- Must not import the deleted legacy accounting services.
- Must not independently implement journal balance rules, lifecycle transitions,
  report formulas, or provider fallback logic.

Public API contracts remain stable during architectural migration.

## Database dependency rules

- Domain and application code depend on repository interfaces, not SQLAlchemy.
- SQLAlchemy models remain infrastructure persistence models under
  `app/modules/accounting/models/` (no directory relocation planned).
- Alembic depends on persistence metadata, never on domain entities.
- Report readers may use optimized SQL behind an application-facing port.
- Repository methods should be purposeful (`get_open_period`,
  `find_postable_entry`) rather than exposing unrestricted query builders.
- Repositories may `flush()` for generated identifiers.  They must not
  `commit()`.

## AI dependency rules

- Application code depends on capabilities such as `JournalSuggestionProvider`
  or `IntentClassifier`, never on Gemini/OpenAI classes.
- Provider configuration and SDK response formats remain in infrastructure.
- Accounting grounding, permissions, company scope, and confirmation policy
  remain provider-neutral.
- Provider failure must be represented in a stable result or application error,
  not leaked as an SDK exception through the API.

## Frontend dependency direction

```text
app/pages -> widgets -> features -> entities -> shared
```

Imports may skip layers toward `shared`, but lower layers must not import pages,
widgets, or app composition.

### App and pages

- `app` owns providers, routes, shell composition, and initialization.
- Pages compose widgets, features, entities, and shared UI.
- Pages should not own deep accounting rules, raw transport handling, large
  mutation implementations, or reusable visual primitives.

### Widgets and features

- Widgets compose several features/entities into a stable page region.
- Features implement a user action and may use entity APIs and shared UI.
- Features should expose a small public interface instead of requiring
  cross-feature deep imports.

### Entities and shared

- Entities own reusable account, journal, company, user, fiscal, and audit-event
  models and entity-specific presentation.
- `shared/api` owns transport mechanics, not domain endpoints or permissions.
- `shared/ui` is business-neutral and must not import feature state.
- `shared/theme` owns semantic visual tokens and chart palettes.

## Styling rules

- Theme colors must be expressed through semantic variables and Tailwind tokens.
- JSX may use layout, spacing, sizing, and responsive utilities directly.
- Normal text and surfaces should not select raw violet/gray/slate palette values
  independently in every component.
- Brand purple is reserved for accents, primary actions, links, focus, and active
  states — not ordinary body or table text.
- Success, warning, danger, debit, and credit colors must have named semantics.
- Dark-mode choices should resolve centrally through tokens rather than repeated
  `dark:` palette pairs where practical.
- Chart colors must come from a central chart theme.

## Enforcement approach

Do not enforce all rules against the current code immediately.  First:

1. Document existing exceptions.
2. Apply rules to new files.
3. Migrate one bounded context.
4. Add checks for that migrated context (with allowlists for existing violations).
5. Expand enforcement only as violations are removed.

Architecture enforcement must never be used to justify changing API contracts,
database schema, accounting results, RBAC, audit atomicity, assistant
confirmation, frontend routes, or RTL behavior.
