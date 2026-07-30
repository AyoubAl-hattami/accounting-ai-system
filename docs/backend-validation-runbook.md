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

The workflow intentionally does not start PostgreSQL or the API server, seed
test data, run the complete backend suite, or invoke Alembic. The existing HTTP
integration suite depends on a configured database, a running API, and known
seed state; reproducing those requirements in CI needs a separately reviewed
test-environment design.

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

If full-suite CI is added later, it should use the same backend working
directory, `PYTHONPATH`, dependency lock input, full pytest command, and
Alembic read-only checks documented above. Database creation, migrations, seed
state, API-server lifecycle, and cleanup must be explicit. Adding those
services remains a separate change because credentials, isolation, and branch
policy require project-level decisions.
