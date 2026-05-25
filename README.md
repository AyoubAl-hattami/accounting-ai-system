# Accounting AI System

A FastAPI + PostgreSQL backend for a multi-company double-entry accounting system with JWT authentication, role-based company access, journal workflows, financial reports, audit logs, default chart of accounts, and opening balance support.

## Current Status

This project currently includes the backend accounting core.

### Implemented Features

- FastAPI backend
- PostgreSQL database
- SQLAlchemy 2.x ORM
- Alembic migrations
- Pydantic v2 schemas
- JWT authentication
- User registration and login
- Company-user role linking
- Company access protection
- Role-based access control for key routes
- Multi-company structure
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
- CORS configuration for future frontend

---

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Pydantic v2
- JWT / python-jose
- passlib + bcrypt
- Uvicorn

---

## Project Structure

```text
backend/
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
│   │   └── security.py
│   └── modules/
│       └── accounting/
│           ├── models/
│           ├── routes/
│           ├── schemas/
│           └── services/
├── .env.example
├── alembic.ini
└── requirements.txt
Local Setup
1. Clone the repository
git clone https://github.com/AyoubAl-hattami/accounting-ai-system.git
cd accounting-ai-system
2. Go to backend folder
cd backend
3. Create virtual environment
python -m venv .venv
4. Activate virtual environment
.venv\Scripts\activate
5. Install dependencies
pip install -r requirements.txt
Environment Variables

Create a .env file inside the backend folder:

copy .env.example .env

Then edit .env:

APP_NAME=Accounting AI System
APP_ENV=development

DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/accounting_ai

SECRET_KEY=replace-with-a-secure-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=1440

Generate a secure secret key:

python -c "import secrets; print(secrets.token_urlsafe(64))"

Paste the generated value into:

SECRET_KEY=...
PostgreSQL Setup

Create the database:

& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres

Inside PostgreSQL:

CREATE DATABASE accounting_ai;
\q
Run Migrations

From the backend folder:

alembic upgrade head
Run the Backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010

Open:

http://127.0.0.1:8010/docs

Health check:

http://127.0.0.1:8010/health

Database health check:

http://127.0.0.1:8010/health/db
Authentication Flow
Register
$base = "http://127.0.0.1:8010"

$registerBody = @{
  email = "admin@example.com"
  password = "Password123"
  full_name = "System Admin"
} | ConvertTo-Json

Invoke-RestMethod -Method Post "$base/auth/register" `
  -ContentType "application/json" `
  -Body $registerBody
Login
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
Current User
Invoke-RestMethod -Method Get "$base/auth/me" `
  -Headers $headers
Company Access

Users are linked to companies through company_users.

Supported roles:

admin
accountant
reviewer
approver
auditor
viewer

Example:

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
Default Chart of Accounts

Seed default accounts for a company:

Invoke-RestMethod "$base/accounts/seed-defaults?company_id=3" `
  -Method Post `
  -Headers $headers

Default accounts include:

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
Journal Entry Workflow

Journal entries follow this workflow:

draft -> reviewed -> posted

Rules:

New entries are created as draft.
Only draft entries can be updated.
Only draft entries can be reviewed.
Draft or reviewed entries can be posted.
Posted entries cannot be edited.
Posted entries must be corrected using reversal entries.
Draft entries can be voided.
Opening Balance Example
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

Review:

Invoke-RestMethod "$base/journal-entries/$($opening.id)/review" `
  -Method Post `
  -Headers $headers

Post:

Invoke-RestMethod "$base/journal-entries/$($opening.id)/post" `
  -Method Post `
  -Headers $headers
Reports
Trial Balance
Invoke-RestMethod "$base/reports/trial-balance?company_id=3" `
  -Headers $headers
Profit and Loss
Invoke-RestMethod "$base/reports/profit-and-loss?company_id=3" `
  -Headers $headers
Balance Sheet
Invoke-RestMethod "$base/reports/balance-sheet?company_id=3" `
  -Headers $headers
Account Ledger
Invoke-RestMethod "$base/reports/account-ledger?company_id=3&account_id=5" `
  -Headers $headers
General Ledger
Invoke-RestMethod "$base/reports/general-ledger?company_id=3" `
  -Headers $headers
Audit Logs
Invoke-RestMethod "$base/audit-logs?company_id=3" `
  -Headers $headers

Audit logs currently track important journal actions, including:

create_journal_entry
update_journal_entry
review_journal_entry
post_journal_entry
reverse_journal_entry
void_journal_entry
create_opening_balance
Development Notes
Run backend
cd C:\ayoub\accounting-ai-system\backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
Create migration
alembic revision --autogenerate -m "message here"
Apply migrations
alembic upgrade head
Save dependencies
pip freeze > requirements.txt
Security Notes
.env must never be committed to Git.
Use .env.example for documentation only.
JWT SECRET_KEY must be strong and private.
Most accounting endpoints require authentication and company access.
Company access is controlled through company_users.
Role-based permissions are partially implemented.
Next Planned Features
More complete RBAC enforcement
Tests
Pagination metadata
Better API response wrappers
AI Agent module
Frontend with React + TypeScript
Invoice extraction
Bank reconciliation
Better reporting UIؤ