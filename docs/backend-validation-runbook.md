# Backend Validation Runbook

This is the canonical developer checklist for validating backend changes on
Windows PowerShell. Run database-dependent commands only against an approved
local or disposable environment, and record any unavailable dependency instead
of reporting a pass.

## Configuration status

- Backend dependencies are pinned in `backend/requirements.txt`.
- Pytest currently uses its standard discovery from `backend/tests`; there is
  no project `pytest.ini` or `pyproject.toml` test configuration.
- Alembic is configured by `backend/alembic.ini` with migrations under
  `backend/alembic`.
- `.github/workflows/backend-validation.yml` provides conservative backend
  validation for pull requests and pushes to `main`.

The lack of project pytest configuration is a documented fact, not an
instruction to add configuration without a separate review of test semantics.

## Automated CI validation

The backend workflow uses Ubuntu and Python 3.13. It:

- Installs the pinned backend requirements with pip caching.
- Compiles `backend/app` to catch Python syntax errors without importing the
  application or contacting external services.
- Runs `backend/tests/test_architecture_guards.py` with pytest caching disabled.
- Searches application, test, documentation, README, and workflow files for
  deleted accounting service references.
- Starts an ephemeral PostgreSQL 16 service with CI-only credentials.
- Applies all Alembic migrations and verifies the current revision and a single
  migration head.
- Starts FastAPI on `127.0.0.1:8010`, waits for `/health/db`, and runs the
  self-contained health, authentication, rate-limit, password-policy, and
  factory-backed report/export tests.

The workflow uses only non-secret, job-local database credentials and sets the
backend configuration explicitly. AI providers remain in deterministic rules
mode with no provider keys.

The workflow intentionally does not run the complete backend suite. Shared
integration fixtures assume an existing admin user, company ID 3, account IDs
5 and 11, and fiscal data that migrations do not seed. Reproducing that state
requires a separately reviewed, deterministic test-data bootstrap rather than
depending on a developer database snapshot or test ordering.

## Deterministic fixture readiness inventory

`backend/tests/fixture_readiness.py` is the source-controlled inventory for the
remaining migration work. `backend/tests/test_fixture_readiness.py` statically
checks that inventory in CI and prevents the workflow from silently enabling
the full suite while the fixture contract is unresolved.

The current inventory identifies:

- 33 modules that make live HTTP requests to the configured API server.
- 25 modules that consume the shared admin/company/account/fiscal seed contract.
- 4 self-contained HTTP modules that create their own state or require no seed.
- 4 factory-backed HTTP modules that create deterministic company/accounting
  state before calling the API.
- 6 modules that directly use the application `SessionLocal` in addition to
  HTTP requests.
- Provider tests that use fake keys and mocked clients rather than external AI
  services.

Already deterministic unit, use-case, repository, architecture, and fixture-
readiness tests can run without the historical seed snapshot. The four
self-contained HTTP modules and four factory-backed report/export modules still
require PostgreSQL and FastAPI, which CI now provides.

`backend/tests/factories/accounting.py` provides the initial deterministic
test-only factory layer. It creates unique users, companies, memberships,
default chart-of-accounts rows, open fiscal years and periods, and optional
balanced journal entries. Tests should consume returned objects or IDs from
the `deterministic_accounting_bootstrap` fixture rather than assuming
`admin@example.com`, company ID 3, account IDs 5 and 11, or fiscal year ID 2.

Factory-backed HTTP modules now include `backend/tests/test_protected_reports.py`,
`backend/tests/test_reports_smoke.py`, `backend/tests/test_report_csv_exports.py`,
and `backend/tests/test_report_pdf_exports.py`. They use the generated
bootstrap company, auth headers, and account IDs instead of shared fixture IDs.

Future fixture phases should migrate the remaining fixed row IDs to this
factory pattern, adding posted journal history only where a test actually
asserts transaction or reporting behavior. Tests must consume returned
identifiers, isolate mutations per run, and clean up without depending on file
order. Only after the implicit-seed inventory reaches zero should CI replace
the subset with `pytest tests -v`.

### CI-equivalent database readiness locally

Only against an approved disposable database, prepare the backend shell and
run:

```powershell
alembic upgrade head
alembic current
alembic heads
```

Start FastAPI as documented below, then in another prepared backend shell run:

```powershell
python -m pytest -p no:cacheprovider `
  tests/test_health.py `
  tests/test_auth.py `
  tests/test_auth_rate_limit.py `
  tests/test_password_policy.py `
  tests/test_protected_reports.py `
  tests/test_reports_smoke.py `
  tests/test_report_csv_exports.py `
  tests/test_report_pdf_exports.py `
  -v
```

The local commands use the database configured in `backend/.env`; verify that
target before applying migrations.

## Shell setup

Start every backend validation shell consistently:

```powershell
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
$env:PYTHONPATH = "C:\ayoub\accounting-ai-system\backend"
```

## Fast static boundary check

For documentation or architecture-only work, the small static guard file can
be run without starting the API server:

```powershell
python -m pytest -p no:cacheprovider tests/test_architecture_guards.py -v
```

This check is not a replacement for the full suite.

## Full backend validation

The complete suite contains HTTP integration tests. Unless a test explicitly
uses an in-process client, start the configured backend and PostgreSQL database
before running it.

In the server terminal:

```powershell
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
$env:PYTHONPATH = "C:\ayoub\accounting-ai-system\backend"
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

In a separate validation terminal:

```powershell
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
$env:PYTHONPATH = "C:\ayoub\accounting-ai-system\backend"
pytest tests -v
```

The integration-test default is `http://127.0.0.1:8010`. To target another
approved test instance, set `ACCOUNTING_TEST_BASE_URL` explicitly before
running pytest.

## Migration-state validation

From the prepared backend shell:

```powershell
alembic current
alembic heads
```

`alembic heads` should report one intended head, and `alembic current` should
identify the revision applied to the selected database. Applying, generating,
or downgrading migrations is a separate, state-changing task and is not part of
this read-only readiness check.

## Repository hygiene

From the repository root:

```powershell
cd C:\ayoub\accounting-ai-system
git status --short
git diff --stat
git diff --name-only
git diff --check
```

Remember that ordinary `git diff` output omits untracked files; use
`git status --short` as the complete file inventory.

## Result checklist

Record:

- Branch and pre-existing worktree changes.
- Exact pytest command and passed, failed, skipped, and warning counts.
- Whether the API server and database were available.
- Alembic current revision and head count.
- Legacy-reference search output, if architecture boundaries changed.
- `git diff --check` result.

Never reuse a historical test or Alembic result as if it were produced by the
current change.

## Warning interpretation

- A pytest cache warning means the runner could not write `.pytest_cache`; it
  does not by itself mean a test failed. The CI architecture command disables
  the cache provider, while local full-suite runs should record any warning.
- Git LF/CRLF messages describe line-ending conversion policy. They are not
  `git diff --check` failures. Do not change repository line-ending policy as a
  side effect of validation work.

## Future full-suite CI parity checklist

If full-suite CI is added later, it should extend the current PostgreSQL job and
retain the same backend working directory, `PYTHONPATH`, dependency lock input,
and full pytest command documented above. The deterministic factory bootstrap
must be applied to the remaining shared-seed consumers with per-run isolation
and cleanup. The readiness guard must be updated as each consumer is migrated.
