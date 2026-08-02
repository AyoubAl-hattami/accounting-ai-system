# Frontend E2E Readiness Plan

**Status date:** 2026-08-02
**Phase:** 65
**Status:** Planning only — Playwright (or any E2E framework) is **not installed**.

---

## Why not implemented now

Playwright is not currently a dependency of `frontend/package.json`, and installing a
new E2E framework plus wiring it into CI is a meaningful scope/risk addition that goes
beyond "cleanup" work. Per the conservative mandate for this phase, we do not install
new tooling speculatively. This document captures the plan so a future phase can
implement it deliberately, with its own validation and CI budget.

Current automated coverage is Vitest + React Testing Library unit/smoke tests only
(see `docs/frontend/ui-smoke-checklist.md`, Phase 64 section). Full user-journey
validation remains manual, per the checklist.

---

## Recommended scope (first E2E pass)

A minimal, high-value first suite should cover the primary user journeys, each as one
Playwright test file:

1. **Login** — unauthenticated redirect to `/login`, invalid credentials show inline
   error, valid credentials land on dashboard, token persists across reload.
2. **Dashboard** — loads after login, shows at least one KPI/chart, loading state
   visible before data, error state on simulated 5xx.
3. **Accounts** — list renders with `AccountTypeBadge`, pagination works, create
   account appears without reload, seed-defaults populates a blank chart of accounts.
4. **Journal entry create** — open "New entry" modal, select accounts (verifies
   `useAccounts`/account picker integration), unbalanced entry disables submit,
   balanced entry submits and appears in the list as draft.
5. **Reports export** — Trial Balance (or Balance Sheet) renders, triggers a CSV/PDF
   download and asserts the download event fires (not necessarily file content).
6. **Audit logs** — list renders, filters narrow results, non-admin user gets 403
   (verified via network response, not by parsing UI copy).
7. **Company users** — list renders with role badges, admin can invite a user,
   pending invitation row appears, non-admin cannot see management actions.

These map directly to the existing manual checklist sections in
`docs/frontend/ui-smoke-checklist.md`, so the manual checklist can be retired
section-by-section as each E2E test is added and proven stable.

---

## Test data strategy

- Run against a **dedicated test backend** (`APP_ENV=test`, same fixture/factory
  approach already used by `backend/tests/`), never against a shared dev/staging DB.
- Seed a deterministic company + admin user + minimal chart of accounts via existing
  backend test factories/fixtures (do not hand-roll new seed logic — reuse
  `backend/tests/factories` patterns already relied on by `test_fixture_readiness.py`).
- Each E2E spec should create its own company/tenant scope where possible (via API
  setup calls in a `beforeEach`/fixture) rather than sharing mutable state across
  specs, to keep tests independent and re-runnable.
- Avoid embedding real secrets; use the same `SECRET_KEY=ci-static-validation-secret-key-not-for-production`
  style throwaway config used by backend guard test runs.

---

## How to run locally (once implemented)

Planned commands (not yet available):

```bash
npm install --prefix frontend -D @playwright/test
npx playwright install --with-deps chromium
# start backend in a separate terminal: APP_ENV=test uvicorn ...
npm run test:e2e --prefix frontend
```

The backend must be running locally (or in a docker-compose test stack) before E2E
tests execute — Playwright would launch the Vite dev server via its `webServer` config,
but the API backend is a separate process that must be started explicitly.

---

## Why not in CI yet

- No E2E framework is installed yet — this is planning only.
- E2E suites require a running backend + database, which is a heavier CI dependency
  than the current frontend-validation workflow (tsc, lint, Vitest, build) — it would
  need a dedicated job with service containers (Postgres) and backend startup, which
  is out of scope for this cleanup phase.
- The backend's own full-suite CI is still deliberately disabled
  (`FULL_SUITE_CI_READY = False`, see `docs/architecture/clean-architecture-migration-status.md`)
  pending fixture-contract stabilization; wiring frontend E2E against a backend whose
  own CI posture is still "manual verification in progress" would add flaky-test risk
  before that foundation is solid.
- Recommendation: revisit E2E CI wiring after Track A's `FULL_SUITE_CI_READY` flips to
  `True`, so both layers graduate to CI enforcement together.

---

## Relationship to existing manual checklist

`docs/frontend/ui-smoke-checklist.md` remains the source of truth for manual QA until
E2E tests are implemented. When a scope item above is implemented as a Playwright test
and proven stable in at least 3 consecutive local runs, mark the corresponding checklist
section as "automated" rather than deleting it, so reviewers can see coverage lineage.
