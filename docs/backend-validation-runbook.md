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
- The repository currently has no `.github/workflows` directory, so backend
  validation is manual rather than CI-enforced.

These absences are documented facts, not instructions to add configuration
without a separate review of test and workflow semantics.

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

## Future CI parity checklist

If CI is added later, it should use the same backend working directory,
`PYTHONPATH`, dependency lock input, full pytest command, and Alembic read-only
checks documented above. Database and API-server lifecycle must be explicit.
Adding CI remains a separate change because service setup, secrets, and branch
policy require project-level decisions.
