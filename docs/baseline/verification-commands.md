# Verification Commands

These commands define the expected verification sequence before and after a
future refactor. They are documentation only and were not run while creating
this baseline.

Run commands only against an approved local or disposable environment. Never
print `.env` contents, and never downgrade an important database.

## 1. Git status

From the repository root:

```powershell
cd C:\ayoub\accounting-ai-system
git status --short
git diff --stat
git diff --name-only
```

Record pre-existing changes before starting. A refactor must not overwrite,
reset, or mix with unrelated work.

## 2. Backend tests

```powershell
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
$env:PYTHONPATH = "C:\ayoub\accounting-ai-system\backend"
pytest tests -v
```

For a narrow change, run the affected focused tests first, then the complete
suite. Record collection count, passed/failed/skipped counts, duration, and full
failure names. Some integration tests may require the existing project test
server or PostgreSQL setup; do not report success when those dependencies are
unavailable.

## 3. PostgreSQL and Alembic verification

Using the project's configured development/test PostgreSQL database:

```powershell
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
$env:PYTHONPATH = "C:\ayoub\accounting-ai-system\backend"
alembic current
alembic heads
```

Expected baseline:

- `alembic heads` reports the intended single current head.
- `alembic current` identifies the database revision.

Applying a migration is a separate state-changing operation. Run it only when
the task requires it and the selected database is approved:

```powershell
alembic upgrade head
```

Only on a disposable database:

```powershell
alembic downgrade -1
alembic upgrade head
```

Never run downgrade verification on important data.

## 4. Frontend build and lint

```powershell
cd C:\ayoub\accounting-ai-system
$env:Path = "C:\nodejs;$env:Path"
npm run build --prefix frontend -- --outDir dist-check
npm run lint --prefix frontend
```

The PATH assignment supplied in some task notes omitted the semicolon:
`"C:\nodejs$env:Path"`. The operational form above includes the required Windows
PATH separator.

### Windows output-directory note

`frontend/dist` may be locked by a browser, preview process, antivirus scanner,
or Windows file handle. Use `--outDir dist-check` for verification instead of
deleting or overwriting a locked `dist` directory. Treat `dist-check` as
generated output; it should not be committed.

## 5. Backend development server

In a dedicated terminal:

```powershell
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
$env:PYTHONPATH = "C:\ayoub\accounting-ai-system\backend"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

API documentation:

- http://127.0.0.1:8010/docs

Use the OpenAPI page to compare endpoint paths, methods, schemas, security
requirements, and documented response codes before and after a refactor.

## 6. Frontend development server

In a separate terminal:

```powershell
cd C:\ayoub\accounting-ai-system
$env:Path = "C:\nodejs;$env:Path"
npm run dev --prefix frontend
```

Browser URL:

- http://localhost:5173

## 7. Manual browser URLs

With both servers running, inspect:

- http://localhost:5173/login
- http://localhost:5173/dashboard
- http://localhost:5173/accounts
- http://localhost:5173/journal-entries
- http://localhost:5173/reports/trial-balance
- http://localhost:5173/reports/profit-and-loss
- http://localhost:5173/reports/balance-sheet
- http://localhost:5173/reports/account-ledger
- http://localhost:5173/reports/general-ledger
- http://localhost:5173/audit-logs
- http://localhost:5173/company-users
- http://localhost:5173/settings
- http://localhost:5173/accept-invite

Protected routes should redirect or deny appropriately when unauthenticated or
unauthorized.

## 8. Reference-run record

For each future phase, record:

- Git revision and working-tree state.
- Python, Node, PostgreSQL, and browser versions.
- Backend test result.
- Alembic current/head result.
- Frontend build and lint result.
- Manual workflow result for affected areas.
- Known environmental failures or skipped checks.

Do not claim that any command passed unless it was actually executed for that
change.
