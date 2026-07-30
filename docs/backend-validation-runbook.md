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
- Starts FastAPI on `127.0.0.1:8010`, waits for `/health/db`, and runs the three
  reproducible health endpoint tests.

The workflow uses only non-secret, job-local database credentials and sets the
backend configuration explicitly. AI providers remain in deterministic rules
mode with no provider keys.

The workflow intentionally does not run the complete backend suite. Shared
integration fixtures assume an existing admin user, company ID 3, account IDs
5 and 11, and fiscal data that migrations do not seed. Reproducing that state
requires a separately reviewed, deterministic test-data bootstrap rather than
depending on a developer database snapshot or test ordering.

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
python -m pytest -p no:cacheprovider tests/test_health.py -v
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
and full pytest command documented above. A deterministic fixture bootstrap,
per-run isolation, and cleanup must replace assumptions about pre-existing row
IDs. Adding that bootstrap remains a separate behavior-preservation task.
