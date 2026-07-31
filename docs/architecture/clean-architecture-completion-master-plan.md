# Clean Architecture Completion Master Plan

This document is the authoritative phase-by-phase plan for completing the
Accounting AI System Clean Architecture migration.  It is generated from the
agent system prompt and should be kept in sync with actual phase completion.

---

## Core decisions (ratified)

1. **Routes own the final transaction commit.**  No UnitOfWork port will be
   introduced.  Routes own auth, RBAC, HTTP translation, audit write, and
   final commit/rollback.
2. **No directory relocations.**  `routes/models/schemas` stay under
   `app/modules/accounting/`.  Boundaries are enforced by import rules and
   guards, not file movement.
3. **Tests and CI foundation come before backend service refactoring.**
4. **Frontend migration is sequenced after backend + CI foundation.**

---

## Current known state (as of phase-19 branch)

- Accounts, Fiscal, Journals, Reports migrated to Clean Architecture.
- Remaining backend domains: companies, users, company-users/RBAC, invitations,
  audit, security/auth, exports, AI providers, assistant/conversations.
- ~20 implicit shared-seed test consumers remain.
- ~9 factory-backed HTTP files.
- `FULL_SUITE_CI_READY = False`.
- Full-suite CI still disabled.
- Alembic head: `a6f4c2d8e1b7`.
- Frontend clean migration: not started.

---

## Absolute hard rules

- Never make broad unbounded refactors.
- Never mix unrelated phases.
- Never change public API behavior unless the phase explicitly requires it.
- Never weaken tests.  Never skip tests.  Never mark tests xfail to pass.
- Never fake AI/Gemini behavior unless tests already use mocks/fakes.
- Never call real external AI services.  Never require real API keys.
- Never introduce UnitOfWork.
- Never move routes/models/schemas out of `app/modules/accounting/`.
- Never silently change transaction ownership.
- Never let the application layer import FastAPI, SQLAlchemy ORM, Pydantic API
  schemas, infrastructure adapters, or external AI SDKs.
- Never let repositories commit.  Never let report repositories mutate.
- Never reintroduce deleted legacy services.
- Never enable full-suite CI until fixture inventory is empty, conftest shared
  seed fixtures are deleted, and order-isolation hardening is done.
- Never continue to the next phase automatically.
- Never commit `.env`, secrets, dumps, logs, `node_modules`, `dist`, or
  generated build outputs.
- Stop immediately if a phase would require package/dependency changes,
  migrations, destructive data reset, unknown credentials, or unrelated runtime
  rewrites.

---

## TRACK A — Test and CI Foundation

### PHASE 19 — Factory correctness core

**Goal:** Fix factory correctness before more tests depend on it.

**Scope:**
- `backend/tests/factories/accounting.py`
- `backend/tests/test_deterministic_factories.py`
- docs only if needed

**Required changes:**
1. `create_open_fiscal_year` should default to current year using
   `app.core.clock.get_today_date`, not hardcoded 2026.
2. Fiscal period `end_date` must use `calendar.monthrange`, not day 28.
3. Default account seeding must preserve `parent_code` hierarchy from
   `DEFAULT_ACCOUNTS`.
4. Seed accounts in two passes:
   - pass 1: create all accounts
   - pass 2: wire `parent_id`
5. Add or update deterministic factory assertions:
   - default period contains today
   - `accounts_by_code["1110"].parent_id == accounts_by_code["1000"].id`
   - `accounts_by_code["4100"].parent_id == accounts_by_code["4000"].id` if
     these codes exist
6. Generalise `create_balanced_journal` into `create_journal(entry_date=, lines=[...])`.
7. Keep `create_balanced_journal` as backward-compatible wrapper.
8. Do not migrate any HTTP test file in this phase.

**Must not change:** runtime code, public API, migrations, CI subset, fixture
readiness counts.

**Acceptance:**
- Factory uses production clock helper.
- Current month period covers the real current month.
- Default chart hierarchy is preserved.
- Existing factory consumers remain compatible.
- No fixture readiness count changes.

---

### PHASE 20 — Factory extension kit + RBAC canary

**Goal:** Add all factory helpers needed by remaining test migrations and migrate
RBAC matrix as a canary.

**Scope:**
- `backend/tests/factories/accounting.py`
- `backend/tests/test_rbac_permission_matrix.py`
- `backend/tests/fixture_readiness.py`
- `backend/tests/test_fixture_readiness.py`
- `.github/workflows/backend-validation.yml`
- `docs/backend-validation-runbook.md`
- `docs/architecture/clean-architecture-migration-status.md`

**Required factory helpers:**
- `add_member(role)`
- `create_superuser()`
- `create_invitation()` — must mirror `f"{invite.id}:{raw_token}"` format
- `create_multi_year_bootstrap()`
- `create_profit_and_loss_data()`
- `create_assistant_conversation()`
- company-scoped `assert_audit_log()`
- `auth_headers_for(user)`

**Migrate:** `test_rbac_permission_matrix.py`

**Rules:**
- Remove direct `SessionLocal` usage from migrated tests if safe.
- Do not assume `admin@example.com`, `company_id=3`, or fixed account IDs.
- Use factory-created users/companies/memberships.

**CI:** Add `test_rbac_permission_matrix.py` to db-backed subset only if fully
deterministic.

**Acceptance:**
- RBAC canary proves multi-role, company scoping, and token-helper design.
- implicit seed count decreases by 1 if fully migrated.
- factory-backed HTTP file count increases by 1 if fully migrated.

---

### PHASE 21 — Trivial implicit-seed batch

**Goal:** Migrate low-risk implicit-seed files to factories.

**Candidate files:**
- `test_fiscal_year_date_protection.py`
- `test_non_journal_audit_logs.py`
- `test_opening_balance_workflow.py`
- `test_protected_companies.py`

**Rules:** Migrate whole files only if safe.  Add only fully deterministic files
to CI.  If a file has hidden shared-state assumptions, migrate safe subset only
and document blocker.

**Acceptance:**
- implicit seed count decreases by fully migrated files.
- CI subset expands only by deterministic full files.

---

### PHASE 22 — Easy batch + reset-script decision

**Goal:** Migrate easy files and make an explicit decision for
`test_reset_script.py`.

**Candidate files:**
- `api/test_company_user_invitations.py`
- `test_fiscal_management.py`
- `test_journal_lifecycle_policy.py`
- `test_protected_audit_logs.py`
- `test_reset_script.py`

**Special rule for `test_reset_script.py`:** Inspect
`backend/scripts/reset_company_data.py`.  Either rewrite tests to actually
invoke and verify script behavior safely, classify old tests as semantically
hollow and replace with meaningful script tests, or defer with explicit blocker
if unsafe.  Use isolated factory-created company only.

**Acceptance:**
- Easy batch files deterministic.
- reset-script decision documented.
- CI subset expanded only for fully deterministic files.

---

### PHASE 23 — Medium batch A

**Goal:** Migrate medium-risk factory consumers.

**Candidate files:**
- `test_dashboard_net_income.py`
- `test_protected_company_users.py`
- `test_protected_journal_entries.py`

**Acceptance:** Files fully deterministic or blockers documented.  CI subset
expanded only for fully deterministic files.

---

### PHASE 24 — Medium batch B + multi-year reports

**Goal:** Migrate multi-year/report-related tests.

**Candidate files:**
- `test_invitation_lifecycle_integrity.py`
- `test_balance_sheet_multi_year.py`

**Acceptance:** Multi-year reports deterministic.  Invitation lifecycle
deterministic or clearly deferred.

---

### PHASE 25 — Assistant HTTP batch A + white-box triage

**Goal:** Migrate assistant-adjacent tests and remove mixed white-box
assumptions.

**Candidate files:**
- `test_semantic_transaction.py`
- `test_gemini_assistant_profit.py`
- `test_gemini_assistant_explain.py`

**Rules:** No real Gemini calls.  Use rules/fakes/mocks only.  Do not weaken
hallucination/grounding tests.

**Acceptance:** Batch A deterministic.  No real AI calls.  No fixed
admin/company/account IDs.

---

### PHASE 26 — Assistant HTTP batch B

**Goal:** Finish remaining assistant HTTP seed consumers.

**Candidate files:**
- `test_gemini_assistant.py`
- `test_assistant_conversations.py`
- any deferred `test_fiscal_management` Gemini test

**Acceptance:** No `admin_headers`/`default_company_id`/default account fixtures
remain in test files.  Remaining blockers documented if inventories cannot yet
be emptied.

---

### PHASE 27 — Isolation hardening

**Goal:** Prove full suite is order-independent before enabling full-suite CI.

**Tasks:**
1. Fix per-IP or per-test rate-limiter bleed in `test_auth_rate_limit.py`.
2. Convert unscoped count assertions to company-scoped assertions.
3. Fix misleading `db.rollback()` after bootstrap commit in `conftest.py`.
4. Add opt-in cleanup fixture gated by `ACCOUNTING_TEST_CLEANUP=1`, off in CI.
5. Prepare instructions for randomized full-suite manual runs.

**Rules:** Keep tests serial.  Do not use `pytest-xdist`.  Do not hide failures.

**Acceptance:** Full suite order-independent.  No rate-limiter bleed remains.
Dirty DB behavior documented.

---

### PHASE 28 — Full-suite CI flip

**Goal:** Enable full backend test suite in CI.

**Tasks:**
1. Set `FULL_SUITE_CI_READY = True`.
2. Delete shared seed fixtures from `conftest.py`.
3. Invert readiness guard.
4. Replace DB-backed subset invocation with `pytest tests -v`.
5. Add guards for no shared seed fixtures and no `create_user_token` imports
   outside factories.

**Acceptance:** Full suite ready flag true.  Inventories empty.  Workflow runs
full backend suite.

---

## TRACK B — Ratification and Instruments

### PHASE 29 — Documentation correction

**Goal:** Correct all architecture docs to match ratified architecture.

**Scope:** `docs/architecture/transaction-boundaries.md`,
`docs/architecture/backend-target-architecture.md`,
`docs/architecture/clean-architecture-roadmap.md`,
`docs/architecture/clean-architecture-migration-status.md`,
`docs/architecture/dependency-rules.md`, `README.md` if needed.

**Acceptance:** Docs do not contradict route-owned transaction boundary.

---

### PHASE 30 — Allowlisted guard scaffolding

**Goal:** Introduce future architecture guards with allowlists of current
violations.

**Add guards:**
- `services/**` must not call `db.commit()` — initial allowlist:
  `audit_service.py`, `assistant_conversation_service.py`
- `services/**` must not import `fastapi` — initial allowlist:
  `company_user_invitation_service.py`
- `application/**` must not import `accounting.services`
- `infrastructure/**` must not import `accounting.services`
- `ports.py` uses `Protocol`, never `ABC`
- `dto.py` dataclasses are `frozen=True, slots=True`
- `app/domain/**` contains no `.py`
- guard caveat: attribute-name matching can false-positive `set.add()`

**Acceptance:** Guards pass with allowlists.

---

## TRACK C — Backend Slices

### PHASE 31 — Audit-A interface hardening

**Goal:** Make audit transaction behavior explicit without changing behavior.

**Tasks:**
1. Add `application/audit/ports.py` and `dto.py`.
2. Change `create_audit_log(..., commit: bool = True)` to require explicit
   commit intent.
3. Keep `create_atomic_audit_log` as documented shim marked for deletion at
   Phase 45.

**Acceptance:** No semantic change.  Commit intent visible at every audit call.

---

### PHASE 32 — Exports infrastructure migration

**Goal:** Move CSV/PDF export formatting behind infrastructure/export ports.

**Acceptance:** Export formatting lives in `infrastructure/exports`.  Behavior
unchanged.

---

### PHASE 33 — Companies clean architecture

**Goal:** Migrate company service pattern to application/use case/repository.

**Acceptance:** Company slice clean.  `company_service` no longer used.

---

### PHASE 34 — Company-users / users clean architecture

**Goal:** Migrate company user membership and user-related slice.

**Acceptance:** `company_user_service` removed or unused.  Use cases
framework-neutral.

---

### PHASE 35 — Security/auth clean architecture

**Goal:** Move auth service to `infrastructure/security` and define security
boundary.

**Acceptance:** `create_user_token` import confined.  Auth routes work
unchanged.

---

### PHASE 36 — Invitations I-1 error taxonomy

**Goal:** Remove FastAPI dependency from invitation service without behavior
change.

**Acceptance:** FastAPI dependency removed from invitation service.
Byte-identical API error contract.

---

### PHASE 37 — Invitations I-2 audit extraction

**Goal:** Remove internal audit commits from invitation flow.

**Acceptance:** Invitation audit writes happen inside route-owned transaction.

---

### PHASE 38 — Invitations I-3 port + repository

**Goal:** Introduce clean ports/repository for invitation lifecycle while
preserving lock behavior.

**Acceptance:** Invitation persistence behind port.  Lock behavior documented
and preserved.

---

### PHASE 39 — Invitations I-4 complete migration

**Goal:** Complete invitation clean architecture migration and delete old service.

**Acceptance:** Invitation slice clean.  No invitation service references.

---

### PHASE 40 — AI providers infrastructure boundary

**Goal:** Move AI provider factory and SDK adapters to `infrastructure/ai`.

**Acceptance:** `google`/`openai` imports confined to `infrastructure/ai`.
Provider behavior unchanged.

---

### PHASE 41 — AI pure logic application migration

**Goal:** Move pure AI assistant logic to application layer.

**Acceptance:** Pure AI logic framework-neutral.  Assistant schemas not imported
by application.

---

### PHASE 42 — Assistant conversations clean boundary

**Goal:** Move assistant conversation persistence to clean boundary and remove
service commits.

**Acceptance:** Conversation persistence clean or near-clean.  Services commit
allowlist reduced.

---

### PHASE 43 — Assistant read model extraction

**Goal:** Extract read-only SQLAlchemy seams from Gemini assistant service
behind ports.

**Acceptance:** Gemini assistant no longer performs direct SQL reads outside
adapter.

---

### PHASE 44 — Assistant orchestration clean migration

**Goal:** Move remaining Gemini assistant orchestration into application use
cases.

**Acceptance:** Assistant orchestration clean.  `ai_routes` behavior-compatible.

---

### PHASE 45 — Audit-B and backend closure

**Goal:** Finish backend clean architecture closure.

**Tasks:**
- Delete `create_atomic_audit_log`.
- Delete `app/modules/accounting/services/` if empty/unused.
- Empty every Phase-30 allowlist.
- Promote guards to unconditional.

**Acceptance:** Backend clean architecture complete.  `services/` gone.  All
guards unconditional.  Full CI ready.

---

## TRACK D — Frontend Clean Migration

### PHASE 46 — Frontend CI
### PHASE 47 — Vitest + smoke tests
### PHASE 48 — Semantic theme tokens
### PHASE 49 — Frontend shared/entities foundation + guard
### PHASE 50 — Accounts frontend pilot
### PHASE 51 — Settings/company frontend migration
### PHASE 52 — Dashboard and audit frontend migration
### PHASE 53 — Company users and invitations frontend migration
### PHASE 54 — Journals frontend migration
### PHASE 55 — Reports frontend migration
### PHASE 56 — Frontend legacy deletion and guard closure

*(Each frontend phase: full vertical migration, preserve URLs/Arabic/RTL,
delete legacy duplicates after migration, guard unconditional at end.)*

---

## Global Definition of Done

The project is done only when:

- All remaining backend domains migrated or explicitly classified as
  out-of-scope.
- `app/modules/accounting/services/` is deleted.
- No legacy service references exist anywhere.
- Every architecture guard is unconditional with empty allowlists.
- `FULL_SUITE_CI_READY = True`.
- `pytest tests -v` passes in CI.
- Fixture inventories are empty.
- `conftest.py` is seed-fixture-free.
- Three randomized full-suite runs pass, including one dirty database run.
- `alembic current == alembic heads` and exactly one head.
- `frontend/src/features/` is deleted.
- Frontend dependency guard is unconditional.
- Frontend typecheck, lint, build, and Vitest pass in CI.
- Docs contain no statement contradicting enforced guards.
- Runtime behavior is preserved (API contracts, accounting results, journal
  lifecycle, RBAC, audit atomicity, AI confirmation safety, frontend URLs,
  Arabic/RTL behavior).
