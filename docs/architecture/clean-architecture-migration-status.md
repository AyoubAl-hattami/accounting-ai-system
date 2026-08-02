# Clean Architecture Migration Status

Status date: 2026-08-02

## Track A — Test and CI Foundation: complete (Phases 19–28)

All 33 HTTP integration test files have been migrated from implicit shared-seed
fixtures to deterministic factory-backed patterns.

- `EXPECTED_IMPLICIT_SEED_CONSUMERS = frozenset()` — empty; no remaining
  implicit seed consumers.
- `EXPECTED_HTTP_INTEGRATION_FILES` — all 33 files inventoried and classified.
- `EXPECTED_SELF_CONTAINED_HTTP_FILES` — 4 self-contained files.
- `EXPECTED_FACTORY_BACKED_HTTP_FILES` — 29 factory-backed files.
- `FULL_SUITE_CI_READY = False` — full-suite CI flip deferred; manual suite
  stabilization is in progress.  Full-suite CI will be enabled once three
  consecutive clean manual runs are verified.

## Track B — Ratification and Instruments: in progress (Phase 29 current)

Phase 29 corrects all architecture documentation to match the ratified
route-owned transaction boundary.  Phase 30 will introduce allowlisted
architecture guards for remaining service-layer violations.

## Track C — Backend Slices: not started

Remaining backend domains (companies, users, company-users/RBAC, invitations,
audit, security/auth, exports, AI providers, assistant/conversations) have not
yet been migrated to use cases + repositories.

## Track D — Frontend Clean Migration: Phase 56 complete (2026-08-02)

**AccountTypeBadge promoted to entity layer.**  Six cross-feature import
violations eliminated; architecture guard allowlist reduced from 7 to 1 entry.
Full status in `docs/architecture/frontend-clean-architecture-status.md`.

Remaining cross-feature coupling: `CreateJournalEntryModal → features/accounts/useAccounts`.
Fix deferred to Phase 57 (requires UI refactor or Vitest dependency addition).

**Phase 57 (Vitest): blocked** — no test framework in package.json.
**Phase 58 (smoke tests): documented** — manual checklist at `docs/frontend/ui-smoke-checklist.md`.
**Phase 59 (backend review): no changes** — backend is stable; further cleanup documented as future work.
**Phase 60 (docs): complete** — `frontend-clean-architecture-status.md` created.

**Phase 61 (real component migration): complete (2026-08-02)** — Vitest + RTL
installed; `useAccounts` promoted to `entities/account`; architecture guard
allowlist emptied to 0 entries. See "Phase 61" section of
`docs/architecture/frontend-clean-architecture-status.md`.

**Phase 62 (features-clean cleanup): complete (2026-08-02)** — `frontend/src/features-clean/`
and `frontend/src/pages-clean/` deleted after grep-proven zero usage; all staged
hooks were already superseded by live `entities/`/`features/` code. Directories
no longer exist in the tree.

**Phase 63 (remaining live feature audit): complete (2026-08-02)** — Reviewed
dashboard, reports, audit, company-users, journals, ai/assistant, entities, shared.
No cross-feature imports or misplaced entity-level code found; no changes required.
Guard test (`node --test frontend/tests/architecture_guard.test.mjs`) passes 4/4.

**Phase 64 (test expansion): complete (2026-08-02)** — Added `auditActionLabels`
and `CompanyUserRoleBadge` smoke tests. Vitest suite: 4 test files, 17 tests, all
passing.

**Phase 65 (E2E readiness): documented, not implemented** — Playwright was not
installed (not already a dependency, and installing it was out of scope per the
conservative mandate). See `docs/frontend/e2e-readiness-plan.md`.

**Phase 66 (backend final cleanup): docs-only, no runtime changes** — Backend
architecture guard suite (`test_architecture_guards.py`, `test_fixture_readiness.py`,
21 tests) re-run and confirmed passing. No backend source files were modified;
remaining backend tech debt (Track C slices) remains documented as future work,
not claimed complete.

**Phase 67 (final release docs): complete (2026-08-02)** — Added
`docs/architecture/final-clean-architecture-release-status.md`; updated this file,
`frontend-clean-architecture-status.md`, `docs/frontend/ui-smoke-checklist.md`,
and added `docs/frontend/e2e-readiness-plan.md`.

## Completed backend slices (Phases 1–18 of the original roadmap)

The accounting backend migration is complete for the Accounts, Fiscal,
Journals, Reports, and AI/Gemini accounting-access slices.

- `backend/app/application/` contains framework-neutral accounting use cases,
  data transfer objects, and repository ports for accounts, fiscal, journals,
  and reports.
- `backend/app/infrastructure/database/sqlalchemy/repositories/` contains the
  concrete SQLAlchemy account, fiscal, journal, and report repositories.
- FastAPI accounting routes assemble repositories and use cases, enforce HTTP
  and access concerns, translate errors, call audit helpers, and own the final
  transaction boundary.
- The Gemini assistant retains response formatting and prompt/context assembly
  while reading accounting data through application-facing seams.

## Ratified boundary decisions (Phase 29)

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
5. **Routes are the composition root.**

## Boundary rules

### Application layer

- Must not import FastAPI or its `Request`, `Depends`, or `HTTPException` types.
- Must not import SQLAlchemy sessions or ORM models.
- Must not import accounting API schemas or Gemini/OpenAI clients.
- Must not call database-session `commit`, `flush`, `add`, or `delete` methods.
- Must not import `app.modules.accounting.services` modules.
- Ports defined using `typing.Protocol`, never `ABC`.
- Command/query DTOs defined as `@dataclass(frozen=True, slots=True)`.

### Repository layer

- May use SQLAlchemy models and sessions to implement application ports.
- Must not import FastAPI or HTTP concerns.
- Must not commit; the route remains the transaction owner.
- Mutation repositories may flush only at their established mutation seams.
- The report repository remains read-only and must not add, delete, flush, or
  commit.

### Routes

- Own authentication, RBAC, company access, HTTP validation/error translation,
  audit integration, and final `db.commit()` / `db.rollback()`.
- May compose application use cases with infrastructure repositories.
- Must not import the deleted legacy accounting services.
- Must not import `app.modules.accounting.services` for migrated slices.

## Removed legacy services

The former account, fiscal, journal, report, and default-account service
modules have been removed.  Static guards prevent their module or class names
from returning under `backend/app` or `backend/tests`.

Legitimate names such as the seed-default-accounts route and use case are not
legacy references and remain supported.

## Known non-clean areas (Track C migration targets)

The completed boundary applies to the migrated accounting slices.  The
following modules remain in `services/` pending Phase 31–45 migration:

- `audit_service.py` — contains internal `db.commit()` calls
- `assistant_conversation_service.py` — contains internal `db.commit()` calls
- `company_user_invitation_service.py` — imports FastAPI `HTTPException`
- `auth_service.py`, `company_service.py`, `company_user_service.py`
- `gemini_assistant_service.py`, `ai_provider_factory.py`, AI providers
- `report_csv_service.py`, `report_pdf_service.py`

## domain/ directory

`backend/app/domain/` is reserved for future policy extraction and currently
contains only README placeholder files.  No `.py` files exist there.  Domain
population is incremental and optional for simple slices.

## Automated guards

`backend/tests/test_architecture_guards.py` statically verifies:

- `test_application_layer_has_no_forbidden_framework_or_adapter_imports`
- `test_application_layer_has_no_database_session_mutations`
- `test_repositories_have_no_http_dependencies_or_commits`
- `test_report_repository_remains_read_only`
- `test_direct_repository_flushes_stay_in_existing_journal_mutations`
- `test_routes_do_not_import_deleted_legacy_accounting_services`
- `test_backend_has_no_deleted_legacy_accounting_references`

`backend/tests/test_fixture_readiness.py` statically verifies:

- `test_http_integration_inventory_is_explicit`
- `test_implicit_seed_consumer_inventory_is_explicit`
- `test_self_contained_http_subset_is_explicit`
- `test_direct_session_inventory_is_explicit`
- `test_migrations_do_not_claim_to_seed_the_shared_test_identity`
- `test_external_provider_inventory_uses_test_doubles`
- `test_ci_keeps_full_suite_disabled_until_fixture_contract_is_replaced`

Phase 30 will add further guards (with allowlists) for service-layer violations
that are scheduled for removal in Track C.

## Manual validation

Run the following from PowerShell after reviewing a backend architecture diff.
The complete developer checklist is in `docs/backend-validation-runbook.md`.

```powershell
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
$env:PYTHONPATH = "C:\ayoub\accounting-ai-system\backend"

python -m pytest -p no:cacheprovider tests/test_architecture_guards.py tests/test_fixture_readiness.py -v
pytest tests -v

alembic current
alembic heads

cd C:\ayoub\accounting-ai-system
git status --short
git diff --stat
git diff --name-only
git diff --check
```
