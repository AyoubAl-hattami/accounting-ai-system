# Local Demo Quickstart

Get the accounting system running locally with realistic data in about five
minutes, then walk a prospective user through every screen.

> **Local development only.** The demo credentials below are documented, shared,
> and weak. Never seed a production database and never reuse these credentials
> outside your machine.

---

## 1. Prerequisites

| Requirement | Notes |
| --- | --- |
| Python virtual environment | `backend\.venv` with `pip install -r backend\requirements.txt` |
| PostgreSQL | Running locally, with the database named in `DATABASE_URL` already created |
| `backend\.env` | Copy from `backend\.env.example` and set `DATABASE_URL` and `SECRET_KEY` |
| Node.js | On `PATH`, or installed at `C:\nodejs` (the frontend helper script adds it automatically) |
| `frontend\.env` | Optional — only needed if the backend is not on `http://127.0.0.1:8010`. Copy from `frontend\.env.example`. |

Create the virtual environment and database once:

```powershell
cd C:\ayoub\accounting-ai-system\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Create the PostgreSQL database (adjust the version in the path if needed):

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE accounting_ai;"
```

---

## 2. Start the backend (also runs migrations)

```powershell
cd C:\ayoub\accounting-ai-system
.\scripts\dev-start-backend.ps1
```

The script activates the virtual environment, sets `APP_ENV=development` and
`AI_JOURNAL_PROVIDER=rules`, runs `alembic upgrade head`, and starts Uvicorn on
<http://127.0.0.1:8010>.

Verify:

```text
http://127.0.0.1:8010/health
http://127.0.0.1:8010/health/db
http://127.0.0.1:8010/docs
```

Leave this terminal running.

---

## 3. Seed the demo data

In a second terminal:

```powershell
cd C:\ayoub\accounting-ai-system
.\scripts\dev-seed-demo.ps1
```

This runs `backend\scripts\seed_demo_data.py`. The seed is **idempotent and
additive** — running it twice creates nothing new and deletes nothing. It
refuses to run when `APP_ENV=production`.

Expected output on a fresh database:

```text
  [created]  user admin@example.com (id 1)
  [created]  company Demo Company Ltd (id 1, USD)
  [created]  membership role=admin
  [accounts] 13 created, 0 already present
  [created]  fiscal year 2026 (open)
  [periods]  12 created, 0 already present
  [journals] 8 created and posted, 0 already present
```

On a second run every line reports `[exists]` / `already present`.

---

## 4. Start the frontend

In a third terminal:

```powershell
cd C:\ayoub\accounting-ai-system
.\scripts\dev-start-frontend.ps1
```

Installs `frontend\node_modules` if missing, then starts Vite on
<http://127.0.0.1:5173>.

---

## 5. Log in

```text
Email:    admin@example.com
Password: Password123
```

Local demo credentials only.

If the user already existed in your database (for example from earlier manual
testing), the seed **does not** change the stored password. To force it back to
the documented value:

```powershell
.\scripts\dev-seed-demo.ps1 --reset-demo-password
```

---

## 6. Demo route checklist

Walk these in order. Select **Demo Company Ltd** in the company switcher first.

| # | Route | What to point at |
| --- | --- | --- |
| 1 | Dashboard | Cash position, net income, recent journal activity |
| 2 | Accounts | 13-account chart, parent/child hierarchy, system accounts |
| 3 | Journal Entries | 8 posted entries including one opening balance |
| 4 | Trial Balance | Debit total equals credit total |
| 5 | Profit & Loss | Revenue, expenses, net profit |
| 6 | Balance Sheet | Assets equal liabilities plus equity |
| 7 | General Ledger | Per-account movement across the whole company |
| 8 | Account Ledger | Pick `1110 Main Bank` — running balance across six lines |
| 9 | Company Users | The demo admin membership |
| 10 | Audit Logs | Trail behind the seeded activity |
| 11 | Settings | Company profile, base currency, light/dark mode |
| 12 | AI Assistant | Works offline with the rules provider (see below) |

### AI Assistant during a demo

`AI_JOURNAL_PROVIDER=rules` is the default in the helper scripts. The assistant
runs entirely locally with no API key and no network call. To demo the LLM-backed
assistant instead, set `GEMINI_API_KEY` (or `OPENAI_API_KEY`) in `backend\.env`
and change `AI_JOURNAL_PROVIDER` to `gemini` (or `openai`). Never commit keys.

---

## 7. Expected demo data

**Company** — Demo Company Ltd, base currency USD, fiscal year for the current
calendar year with all twelve months open.

**Chart of accounts** — the standard 13-account default chart:

```text
1000 Assets              2000 Liabilities        3000 Equity
1110 Main Bank           2100 Accounts Payable   3100 Owner Capital
1200 Accounts Receivable                         3200 Retained Earnings

4000 Income              5000 Expenses
4100 Sales Revenue       5100 Rent Expense
                         5200 Software Expense
```

`5200 Software Expense` doubles as the office software/supplies account — the
seed reuses the shipped default chart rather than inventing new accounts.

**Journal entries** — eight balanced entries, all reviewed and posted. Dates are
computed from today: the opening balance sits on 1 January of the current fiscal
year, and the remaining entries are spread across the current month and the two
preceding months (clamped so nothing lands in the future or outside the year).

| Entry no | Description | Debit | Credit |
| --- | --- | --- | --- |
| `DEMO-OB-0001` | Opening balances | 1110 Main Bank 50,000.00 | 3100 Owner Capital 50,000.00 |
| `DEMO-JE-0001` | Cash sales received in bank | 1110 Main Bank 18,500.00 | 4100 Sales Revenue 18,500.00 |
| `DEMO-JE-0002` | Office rent paid | 5100 Rent Expense 2,400.00 | 1110 Main Bank 2,400.00 |
| `DEMO-JE-0003` | Software and supplies on account | 5200 Software Expense 1,250.00 | 2100 Accounts Payable 1,250.00 |
| `DEMO-JE-0004` | Service income invoiced on credit | 1200 Accounts Receivable 9,750.00 | 4100 Sales Revenue 9,750.00 |
| `DEMO-JE-0005` | Customer settled invoices | 1110 Main Bank 6,250.00 | 1200 Accounts Receivable 6,250.00 |
| `DEMO-JE-0006` | Part payment of supplier invoice | 2100 Accounts Payable 500.00 | 1110 Main Bank 500.00 |
| `DEMO-JE-0007` | Office rent paid | 5100 Rent Expense 2,400.00 | 1110 Main Bank 2,400.00 |

**Resulting report figures**

```text
Trial Balance    total debit  91,050.00   total credit 91,050.00
Profit & Loss    income       28,250.00   expenses      6,050.00   net profit 22,200.00
Balance Sheet    assets       72,950.00   liabilities     750.00   equity     72,200.00
Account Ledger   1110 Main Bank closing balance 69,450.00 across 6 lines
General Ledger   movement on 7 accounts
```

---

## 8. Troubleshooting

**PostgreSQL not running**

`dev-start-backend.ps1` fails during `alembic upgrade head` with a connection
error. Start the service and retry:

```powershell
Get-Service postgresql*
Start-Service postgresql-x64-18
```

Also confirm `DATABASE_URL` in `backend\.env` points at a database that exists.

**Port 8010 already in use**

```powershell
Get-NetTCPConnection -LocalPort 8010 | Select-Object OwningProcess
Get-Process -Id <pid>
```

Stop the old Uvicorn process, or start on another port and update
`VITE_API_BASE_URL` in `frontend\.env` to match.

**Frontend port already in use**

Vite falls back to 5174 and prints the URL it actually bound. If the backend
`CORS_ORIGINS` does not include that origin, add it in `backend\.env` and restart
the backend.

**Login fails**

The seed never overwrites an existing user's password. If `admin@example.com`
predates the seed, its password is whatever you set originally. Reset it:

```powershell
.\scripts\dev-seed-demo.ps1 --reset-demo-password
```

Repeated failed attempts are rate limited (`AUTH_FAILED_LOGIN_LIMIT`, default 5
per minute). Wait a minute and retry.

**No companies visible after login**

The user needs an active `company_users` membership. Re-run the seed — it creates
the admin membership if missing and warns if an existing membership is inactive
or not an admin role.

**Reports are empty**

Reports only include journal entries with status `posted`. Confirm the Journal
Entries page shows eight posted entries, and that you selected **Demo Company
Ltd** rather than another company. If the seed reported
`0 created, 8 already present` but the reports are empty, the entries belong to a
different company — check the company switcher.

**Seed refuses to run**

`APP_ENV` is set to `production`. The helper script sets it to `development`; if
you are running the Python script directly, set it yourself.

---

## 9. Production warning

- `admin@example.com` / `Password123` are **local demo credentials only**.
- Never run `seed_demo_data.py` against a production or shared database.
- The script hard-refuses when `APP_ENV=production`, but that guard is a
  backstop, not a policy — do not point it at production by relabelling the
  environment.
- Never commit `backend\.env`, `frontend\.env`, or any API key.
