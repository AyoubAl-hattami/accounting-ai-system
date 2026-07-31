# Clean Architecture Migration Status

Status date: 2026-07-30

The accounting backend migration is complete for the Accounts, Fiscal,
Journals, Reports, and AI/Gemini accounting-access slices. Phase 8 adds static
dependency guards and records the resulting boundary; it does not change
business behavior.

## Completed phases

1. Clean Architecture foundation and migration baseline.
2. Accounts application and repository migration.
3. Fiscal application and repository migration.
4. Journals application and repository migration.
5. Reports application and read-repository migration.
6. AI/Gemini accounting access migration to application seams.
7. Removal of the legacy account, fiscal, journal, report, and default-account
   services after their consumers were migrated.
8. Architecture boundary, legacy-reference, and transaction guard coverage.
9. Backend validation runbook and documentation consistency polish.
10. Conservative pull-request and `main`-branch backend CI validation.
11. PostgreSQL migration, FastAPI startup, and database-health CI readiness.
12. Static deterministic-fixture inventory and full-suite enablement guard.
13. Initial deterministic backend test factories and first HTTP fixture
    migration.
14. Factory-backed report smoke and report export HTTP test migration.

## Current backend architecture

- `backend/app/application/` contains framework-neutral accounting use cases,
  data transfer objects, and repository ports.
- `backend/app/infrastructure/database/sqlalchemy/repositories/` contains the
  concrete SQLAlchemy account, fiscal, journal, and report repositories.
- FastAPI accounting routes assemble repositories and use cases, enforce HTTP
  and access concerns, translate errors, call audit helpers, and own the final
  transaction boundary.
- The Gemini assistant retains response formatting and prompt/context assembly
  while reading accounting data through application-facing seams.

## Boundary rules

### Application layer

- Must not import FastAPI or its `Request`, `Depends`, or `HTTPException`
  types.
- Must not import SQLAlchemy sessions or ORM models.
- Must not import accounting API schemas or Gemini/OpenAI clients.
- Must not call database-session `commit`, `flush`, `add`, or `delete` methods.

### Repository layer

- May use SQLAlchemy models and sessions to implement application ports.
- Must not import FastAPI or HTTP concerns.
- Must not commit; the route remains the transaction owner.
- Mutation repositories may flush only at their established mutation seams.
- The report repository remains read-only and must not add, delete, flush, or
  commit.

### Routes

- Own authentication, RBAC, company access, HTTP validation/error translation,
  audit integration, and final commit/rollback behavior.
- May compose application use cases with infrastructure repositories.
- Must not import the deleted legacy accounting services.

## Removed legacy services

The former account, fiscal, journal, report, and default-account service
modules have been removed. Static guards prevent their module or class names
from returning under `backend/app` or `backend/tests`.

Legitimate names such as the seed-default-accounts route and use case are not
legacy references and remain supported.

## Known non-clean areas

The completed boundary applies to the migrated accounting slices. Other
backend modules, including company, user, invitation, audit, conversation,
authentication, and export workflows, may still use module-service patterns.
They are outside this migration and should be handled as separate behavior-
preserving slices.

## Automated guards

`backend/tests/test_architecture_guards.py` statically verifies application
imports and session calls, repository HTTP/transaction rules, report-reader
immutability, the existing journal flush allowlist, and absence of deleted
legacy accounting references.

`.github/workflows/backend-validation.yml` installs existing backend
dependencies, compiles backend sources, runs the architecture guards, and
checks for deleted-service references. Its database-backed job starts an
ephemeral PostgreSQL service, applies and inspects Alembic migrations, starts
FastAPI, verifies database health, and runs the self-contained health,
authentication, rate-limit, password-policy, and factory-backed report/export
tests.

The full HTTP integration suite remains manual because its shared fixtures
assume pre-existing user, company, account, and fiscal rows that migrations do
not create. `backend/tests/fixture_readiness.py` records the exact HTTP,
implicit-seed, and direct-session consumers, and CI fails if that inventory
drifts without review. `backend/tests/factories/accounting.py` is the initial
test-only factory foundation for replacing fixed IDs with generated users,
companies, memberships, default accounts, fiscal periods, and optional journal
data. `test_protected_reports.py`, `test_reports_smoke.py`,
`test_report_csv_exports.py`, and `test_report_pdf_exports.py` are now
factory-backed. Full-suite CI still requires migrating the remaining 25
implicit-seed consumers to deterministic factories with isolation and cleanup.

## Historical validation baseline

The latest known full-suite result belongs to Phase 7: **673 passed, 3
skipped**. The recorded Alembic head was `a6f4c2d8e1b7`. These are historical
results, not Phase 8 validation claims.

## Manual validation

Run the following from PowerShell after reviewing a backend architecture diff.
The complete developer checklist is in
`docs/backend-validation-runbook.md`.

```powershell
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
$env:PYTHONPATH = "C:\ayoub\accounting-ai-system\backend"

pytest tests -v

alembic current
alembic heads

cd C:\ayoub\accounting-ai-system

git status --short
git diff --stat
git diff --name-only
git diff --check
```

The architecture guard includes the legacy-reference check. Newly added,
untracked files appear in `git status`, but not in ordinary `git diff` output
until staged.
