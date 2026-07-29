# Phase 1 Scaffolding

## What was created

Phase 1 creates the documented target directory shape for:

- Backend domain, application, infrastructure, and interface layers.
- Backend bounded areas for accounting, fiscal policy, identity, companies,
  audit, AI, accounts, journals, reports, users, invitations, and assistant use
  cases.
- Backend infrastructure areas for SQLAlchemy repositories/mappers, AI,
  security, audit, and exports.
- Frontend app, shared, entities, feature migration, widgets, and page migration
  layers.
- Temporary `features-clean` and `pages-clean` namespaces that cannot conflict
  with the current working `features` and route/page organization.

Every created runtime-tree directory contains only a `README.md`.

## Why README files only

README files make intended ownership visible without introducing executable
modules, build inputs, imports, side effects, or registration behavior. They
state what may move later and, equally importantly, what does not belong in each
folder.

This phase is structural documentation. It is not a partial refactor.

## Why backend has no `__init__.py`

No `__init__.py` files were created because Phase 1 must not introduce Python
packages that could be imported prematurely, discovered by tooling, or mistaken
for implemented architecture. Package initialization will be added only for an
approved bounded pilot with baseline verification and explicit import changes.

Existing runtime code remains under `backend/app/modules/accounting` and current
`backend/app/core` locations.

## Why frontend folders are not wired

The new frontend folders contain no TypeScript, React, CSS, barrel exports, route
registrations, or imports. `features-clean` and `pages-clean` intentionally avoid
colliding with existing `frontend/src/features`, `frontend/src/components`, and
`frontend/src/routes`.

Current route URLs, lazy imports, application providers, theme behavior, and
Arabic/RTL behavior therefore remain untouched.

## Incremental migration

Future phases migrate one bounded area at a time:

1. Select a lower-risk pilot such as Accounts or fiscal settings.
2. Identify applicable risks in `docs/baseline/regression-risk-map.md`.
3. Execute and record the relevant baseline before changing imports.
4. Add only the package/code needed for that pilot.
5. Keep existing API, database, accounting, RBAC, audit, and UI contracts stable.
6. Verify parity before removing or redirecting any old implementation.
7. Use a dedicated commit with a clear rollback path.

Journal lifecycle, report calculations, and the Gemini/global assistant are not
appropriate first pilots.

## Rules for future migration

- No behavior change is permitted without baseline verification and explicit
  approval.
- Do not combine backend and frontend refactoring in the same commit.
- Do not migrate journal or report internals before a safer pilot proves the
  boundaries and transaction approach.
- Do not import from new folders until a specific pilot is approved.
- Do not move existing code merely to satisfy the target tree.
- Do not change API contracts, database schema, Alembic history, accounting
  calculations, journal lifecycle, RBAC/company isolation, audit atomicity, AI
  confirmation safety, frontend routes, or Arabic/RTL as incidental cleanup.
- Add package markers, exports, route wiring, and dependency enforcement only
  when the relevant migration slice requires them.
- Remove compatibility code only after all callers migrate and the full
  applicable baseline passes.

## Current status

Scaffolding only. No runtime code is present in the new directories, no imports
reference them, and no behavior is intended to change.
