# Accounting AI System

A FastAPI + PostgreSQL backend for a multi-company double-entry accounting system.

The system currently includes authentication, company access control, role-based permissions, chart of accounts, fiscal years and periods, journal entry workflows, financial reports, audit logs, default account seeding, opening balances, pagination, and backend smoke tests.

---

## Run the demo

To get a working local instance with realistic data in a few minutes, follow the
[local demo quickstart](docs/demo/local-demo-quickstart.md):

```powershell
cd C:\ayoub\accounting-ai-system
.\scripts\dev-start-backend.ps1     # migrations + API on 127.0.0.1:8010
.\scripts\dev-seed-demo.ps1         # idempotent demo user, company, chart, journals
.\scripts\dev-start-frontend.ps1    # Vite dev server on 127.0.0.1:5173
```

The seed data and its credentials are for local development only — see the
quickstart for the full checklist, expected report figures, and troubleshooting.
The manual setup below remains the reference for everything the helper scripts do.

To show that local instance to someone who is not in the room,
`.\scripts\start-public-demo.ps1` puts it behind a single temporary Cloudflare
Quick Tunnel link — see the
[free public local demo tunnel](docs/demo/free-public-local-demo-tunnel.md).
That is a demo tunnel, not production hosting.

---

## Current Status

Backend MVP is active and tested.

### Implemented

- FastAPI backend
- PostgreSQL database
- SQLAlchemy 2.x ORM
- Alembic migrations
- Pydantic v2 schemas
- JWT authentication
- User registration and login
- `/auth/me`
- Company-user linking
- Company access protection
- Role-based permissions
- Multi-company support
- Chart of accounts
- Default chart of accounts seeding
- Fiscal years
- Fiscal periods
- Journal entries
- Journal lines
- Double-entry validation
- Draft / reviewed / posted workflow
- Void draft entries
- Reversal entries
- Opening balances
- Trial balance report
- Profit and loss report
- Balance sheet report
- Account ledger report
- General ledger report
- Audit logs
- CORS setup for frontend
- Paginated list responses
- Backend smoke/integration tests

---

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Pydantic v2
- Uvicorn
- JWT / python-jose
- passlib + bcrypt
- pytest
- requests

---

## Project Structure

```text
accounting-ai-system/
├── README.md
├── BACKEND_API_CHECKLIST.md
├── .gitignore
└── backend/
    ├── .env.example
    ├── alembic.ini
    ├── requirements.txt
    ├── alembic/
    │   ├── env.py
    │   └── versions/
    ├── app/
    │   ├── main.py
    │   ├── core/
    │   │   ├── auth_dependencies.py
    │   │   ├── company_access.py
    │   │   ├── config.py
    │   │   ├── database.py
    │   │   ├── pagination.py
    │   │   └── security.py
    │   └── modules/
    │       └── accounting/
    │           ├── models/
    │           ├── routes/
    │           ├── schemas/
    │           └── services/
    └── tests/
        ├── test_auth.py
        ├── test_default_accounts_seed.py
        ├── test_health.py
        ├── test_opening_balance_workflow.py
        ├── test_protected_accounts.py
        ├── test_protected_audit_logs.py
        ├── test_protected_companies.py
        ├── test_protected_company_users.py
        ├── test_protected_fiscal.py
        ├── test_protected_journal_entries.py
        ├── test_protected_reports.py
        └── test_reports_smoke.py
```

---

## Local Setup

### 1. Clone the repository

```powershell
git clone https://github.com/AyoubAl-hattami/accounting-ai-system.git
cd accounting-ai-system
```

### 2. Go to backend folder

```powershell
cd backend
```

### 3. Create virtual environment

```powershell
python -m venv .venv
```

### 4. Activate virtual environment

```powershell
.venv\Scripts\activate
```

### 5. Install dependencies

```powershell
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file inside the `backend` folder:

```powershell
copy .env.example .env
```

Edit:

```text
backend/.env
```

Example:

```env
APP_NAME=Accounting AI System
APP_ENV=development
APP_VERSION=0.1.0

DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/accounting_ai

SECRET_KEY=replace-with-a-secure-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

Generate a secure secret key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Paste the generated value into:

```env
SECRET_KEY=...
```

Important:

```text
.env must never be committed to Git.
```

---

## PostgreSQL Setup

Create the database:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres
```

Inside PostgreSQL:

```sql
CREATE DATABASE accounting_ai;
\q
```

If your PostgreSQL version is not 18, adjust the path accordingly.

---

## Run Migrations

From the `backend` folder:

```powershell
alembic upgrade head
```

---

## Run the Backend

```powershell
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

Open Swagger:

```text
http://127.0.0.1:8010/docs
```

Health checks:

```text
http://127.0.0.1:8010/health
http://127.0.0.1:8010/health/db
http://127.0.0.1:8010/health/version
```

---

## Authentication

### Register

```powershell
$base = "http://127.0.0.1:8010"

$registerBody = @{
  email = "admin@example.com"
  password = "Password123"
  full_name = "System Admin"
} | ConvertTo-Json

Invoke-RestMethod -Method Post "$base/auth/register" `
  -ContentType "application/json" `
  -Body $registerBody
```

### Login

```powershell
$loginBody = @{
  email = "admin@example.com"
  password = "Password123"
} | ConvertTo-Json

$tokenResponse = Invoke-RestMethod -Method Post "$base/auth/login" `
  -ContentType "application/json" `
  -Body $loginBody

$token = $tokenResponse.access_token

$headers = @{
  Authorization = "Bearer $token"
}
```

### Current User

```powershell
Invoke-RestMethod -Method Get "$base/auth/me" `
  -Headers $headers
```

---

## Company Access

Users are linked to companies through `company_users`.

Supported roles:

```text
admin
accountant
reviewer
approver
auditor
viewer
```

Example link:

```powershell
$companyUserBody = @{
  company_id = 3
  user_id = 1
  role = "admin"
  is_active = $true
} | ConvertTo-Json

Invoke-RestMethod -Method Post "$base/company-users" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $companyUserBody
```

---

## Pagination Format

List endpoints return paginated responses:

```json
{
  "items": [],
  "total": 0,
  "skip": 0,
  "limit": 100
}
```

Currently paginated endpoints include:

```text
GET /companies
GET /accounts
GET /journal-entries
GET /audit-logs
GET /fiscal-years
GET /fiscal-periods
GET /company-users
```

Reports return report-specific objects directly.

---

## Default Chart of Accounts

Seed default accounts for a company:

```powershell
Invoke-RestMethod "$base/accounts/seed-defaults?company_id=3" `
  -Method Post `
  -Headers $headers
```

Default accounts include:

```text
1000 Assets
1110 Main Bank
1200 Accounts Receivable
2000 Liabilities
2100 Accounts Payable
3000 Equity
3100 Owner Capital
4000 Income
4100 Sales Revenue
5000 Expenses
5100 Rent Expense
5200 Software Expense
```

---

## Journal Entry Workflow

Journal entries follow this workflow:

```text
draft -> reviewed -> posted
```

Rules:

- New journal entries are created as `draft`.
- Only draft entries can be updated.
- Only draft entries can be reviewed.
- Draft or reviewed entries can be posted.
- Posted entries cannot be edited.
- Posted entries must be corrected using reversal entries.
- Draft entries can be voided.

---

## Opening Balance Example

```powershell
$openingBody = @{
  company_id = 3
  entry_no = "OB-" + (Get-Date -Format "yyyyMMddHHmmss")
  entry_date = "2026-01-01"
  description = "Opening balances"
  lines = @(
    @{
      account_id = 5
      debit = 5000
      credit = 0
      description = "Opening bank balance"
    },
    @{
      account_id = 11
      debit = 0
      credit = 5000
      description = "Opening owner capital"
    }
  )
} | ConvertTo-Json -Depth 20

$opening = Invoke-RestMethod "$base/journal-entries/opening-balance" `
  -Method Post `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $openingBody
```

Review:

```powershell
Invoke-RestMethod "$base/journal-entries/$($opening.id)/review" `
  -Method Post `
  -Headers $headers
```

Post:

```powershell
Invoke-RestMethod "$base/journal-entries/$($opening.id)/post" `
  -Method Post `
  -Headers $headers
```

---

## Reversal Entry

A posted journal entry is not edited or deleted.

To correct a posted entry, create a reversal:

```http
POST /journal-entries/{journal_entry_id}/reverse
```

Example body:

```json
{
  "entry_no": "REV-0001",
  "entry_date": "2026-01-16",
  "description": "Reverse incorrect entry"
}
```

The reversal entry is created as `draft`, then it can be reviewed and posted.

---

## Void Draft Entry

A draft entry can be voided:

```http
POST /journal-entries/{journal_entry_id}/void
```

Only entries with:

```text
status = draft
```

can be voided.

---

## Reports

All reports require authentication and company access.

### Trial Balance

```powershell
Invoke-RestMethod "$base/reports/trial-balance?company_id=3" `
  -Headers $headers
```

Optional:

```text
as_of_date=2026-01-31
```

### Profit and Loss

```powershell
Invoke-RestMethod "$base/reports/profit-and-loss?company_id=3" `
  -Headers $headers
```

Optional:

```text
start_date=2026-01-01
end_date=2026-01-31
```

### Balance Sheet

```powershell
Invoke-RestMethod "$base/reports/balance-sheet?company_id=3" `
  -Headers $headers
```

Optional:

```text
as_of_date=2026-01-31
```

### Account Ledger

```powershell
Invoke-RestMethod "$base/reports/account-ledger?company_id=3&account_id=5" `
  -Headers $headers
```

Optional:

```text
start_date=2026-01-01
end_date=2026-01-31
```

### General Ledger

```powershell
Invoke-RestMethod "$base/reports/general-ledger?company_id=3" `
  -Headers $headers
```

Optional:

```text
start_date=2026-01-01
end_date=2026-01-31
```

---

## Audit Logs

```powershell
Invoke-RestMethod "$base/audit-logs?company_id=3" `
  -Headers $headers
```

Optional filters:

```text
entity_type=journal_entry
entity_id=1
skip=0
limit=100
```

Audit logs currently track important journal actions, including:

```text
create_journal_entry
update_journal_entry
review_journal_entry
post_journal_entry
reverse_journal_entry
void_journal_entry
create_opening_balance
```

---

## CORS

The backend allows frontend development origins:

```text
http://localhost:5173
http://127.0.0.1:5173
http://localhost:3000
http://127.0.0.1:3000
```

---

## Tests

The suite contains both isolated tests and HTTP integration tests. Integration
tests expect the backend server to be running at:

```text
http://127.0.0.1:8010
```

Run the backend first:

```powershell
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
$env:PYTHONPATH = "C:\ayoub\accounting-ai-system\backend"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

Then in another terminal:

```powershell
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
$env:PYTHONPATH = "C:\ayoub\accounting-ai-system\backend"
pytest tests -v
```

See the [backend validation runbook](docs/backend-validation-runbook.md) for
database prerequisites, the fast architecture check, Alembic state checks, and
the result-recording checklist. Do not treat a historical test count as the
expected result for a new change.

Pull requests and pushes to `main` run the conservative backend workflow in
`.github/workflows/backend-validation.yml`. It compiles backend sources, runs
the architecture guards, checks for deleted accounting service references,
applies migrations to an ephemeral PostgreSQL service, starts FastAPI, and runs
the self-contained health/authentication test subset plus factory-backed report
and report-export tests. It also guards the explicit fixture-readiness
inventory. The full integration suite remains manual until the remaining
pre-existing fixture assumptions are migrated to deterministic factories.

---

## Development Commands

### Run backend

```powershell
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

### Create migration

```powershell
alembic revision --autogenerate -m "message here"
```

### Apply migrations

```powershell
alembic upgrade head
```

### Save dependencies

```powershell
pip freeze > requirements.txt
```

### Run tests

```powershell
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
$env:PYTHONPATH = "C:\ayoub\accounting-ai-system\backend"
pytest tests -v
```

---

## Git Workflow

From the project root:

```powershell
cd C:\ayoub\accounting-ai-system

git status
git add .
git commit -m "Your commit message"
git push
```

---

## Security Notes

- `.env` must never be committed to Git.
- Use `.env.example` for documentation only.
- JWT `SECRET_KEY` must be strong and private.
- Most accounting endpoints require authentication.
- Company access is controlled through `company_users`.
- Role-based permissions are applied on key operations.
- Audit logs now use the current user email as actor for journal actions.

---

## Current Test Coverage

The current tests cover:

```text
health check
database health
version endpoint
register / login / auth-me
protected reports
protected accounts
protected journal entries
protected audit logs
protected companies
protected company users
protected fiscal years / periods
opening balance workflow
default accounts seed
full reports smoke test
pagination metadata
```

---

## Next Planned Features

- Complete pagination cleanup if more list endpoints are added
- Stronger unit tests with FastAPI TestClient
- Better test database isolation
- Frontend with React + TypeScript + Vite
- AI Agent backend layer
- Invoice extraction
- Bank reconciliation
- Better reporting UI
- Deployment setup
