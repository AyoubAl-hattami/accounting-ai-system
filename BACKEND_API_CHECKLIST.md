# Backend API Checklist

## Base URL

```text
http://127.0.0.1:8010
```

---

## Authentication

### Register

```http
POST /auth/register
```

Body:

```json
{
  "email": "admin@example.com",
  "password": "Password123",
  "full_name": "System Admin"
}
```

### Login

```http
POST /auth/login
```

Body:

```json
{
  "email": "admin@example.com",
  "password": "Password123"
}
```

Returns:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

### Current User

```http
GET /auth/me
```

Headers:

```http
Authorization: Bearer <token>
```

---

## Companies

### List companies for current user

```http
GET /companies?skip=0&limit=100
```

Headers:

```http
Authorization: Bearer <token>
```

Response:

```json
{
  "items": [],
  "total": 0,
  "skip": 0,
  "limit": 100
}
```

### Create company

```http
POST /companies
```

After creation, the current user is automatically linked as `admin`.

### Get company

```http
GET /companies/{company_id}
```

### Update company

```http
PATCH /companies/{company_id}
```

Requires role:

```text
admin
```

---

## Company Users

### List company users

```http
GET /company-users?company_id=3&skip=0&limit=100
```

Requires role:

```text
admin, auditor
```

### Add user to company

```http
POST /company-users
```

Requires role:

```text
admin
```

Body:

```json
{
  "company_id": 3,
  "user_id": 1,
  "role": "admin",
  "is_active": true
}
```

### Update company user

```http
PATCH /company-users/{company_user_id}
```

Requires role:

```text
admin
```

---

## Accounts

### List accounts

```http
GET /accounts?company_id=3&skip=0&limit=100
```

Response:

```json
{
  "items": [],
  "total": 0,
  "skip": 0,
  "limit": 100
}
```

### Seed default chart of accounts

```http
POST /accounts/seed-defaults?company_id=3
```

Requires role:

```text
admin, accountant
```

### Create account

```http
POST /accounts
```

Requires role:

```text
admin, accountant
```

### Get account

```http
GET /accounts/{account_id}
```

### Update account

```http
PATCH /accounts/{account_id}
```

Requires role:

```text
admin, accountant
```

---

## Fiscal Years

### List fiscal years

```http
GET /fiscal-years?company_id=3&skip=0&limit=100
```

### Create fiscal year

```http
POST /fiscal-years
```

Requires role:

```text
admin
```

### Get fiscal year

```http
GET /fiscal-years/{fiscal_year_id}
```

### Update fiscal year

```http
PATCH /fiscal-years/{fiscal_year_id}
```

Requires role:

```text
admin
```

---

## Fiscal Periods

### List fiscal periods

```http
GET /fiscal-periods?company_id=3&skip=0&limit=100
```

Optional:

```http
GET /fiscal-periods?company_id=3&fiscal_year_id=2
```

### Create fiscal period

```http
POST /fiscal-periods
```

Requires role:

```text
admin
```

### Get fiscal period

```http
GET /fiscal-periods/{fiscal_period_id}
```

### Update fiscal period

```http
PATCH /fiscal-periods/{fiscal_period_id}
```

Requires role:

```text
admin
```

---

## Journal Entries

### List journal entries

```http
GET /journal-entries?company_id=3&skip=0&limit=100
```

Optional status filter:

```http
GET /journal-entries?company_id=3&status=posted
```

Response:

```json
{
  "items": [],
  "total": 0,
  "skip": 0,
  "limit": 100
}
```

### Create manual journal entry

```http
POST /journal-entries
```

Requires role:

```text
admin, accountant
```

### Create opening balance

```http
POST /journal-entries/opening-balance
```

Requires role:

```text
admin, accountant
```

### Get journal entry

```http
GET /journal-entries/{journal_entry_id}
```

### Update draft journal entry

```http
PATCH /journal-entries/{journal_entry_id}
```

Requires role:

```text
admin, accountant
```

Only allowed when:

```text
status = draft
```

### Review journal entry

```http
POST /journal-entries/{journal_entry_id}/review
```

Requires role:

```text
admin, accountant, reviewer
```

### Post journal entry

```http
POST /journal-entries/{journal_entry_id}/post
```

Requires role:

```text
admin, approver
```

### Reverse posted journal entry

```http
POST /journal-entries/{journal_entry_id}/reverse
```

Requires role:

```text
admin, accountant, approver
```

### Void draft journal entry

```http
POST /journal-entries/{journal_entry_id}/void
```

Requires role:

```text
admin, accountant
```

---

## Reports

All reports require company access.

### Trial Balance

```http
GET /reports/trial-balance?company_id=3
```

Optional:

```http
GET /reports/trial-balance?company_id=3&as_of_date=2026-01-31
```

### Profit and Loss

```http
GET /reports/profit-and-loss?company_id=3
```

Optional:

```http
GET /reports/profit-and-loss?company_id=3&start_date=2026-01-01&end_date=2026-01-31
```

### Balance Sheet

```http
GET /reports/balance-sheet?company_id=3
```

Optional:

```http
GET /reports/balance-sheet?company_id=3&as_of_date=2026-01-31
```

### Account Ledger

```http
GET /reports/account-ledger?company_id=3&account_id=5
```

Optional:

```http
GET /reports/account-ledger?company_id=3&account_id=5&start_date=2026-01-01&end_date=2026-01-31
```

### General Ledger

```http
GET /reports/general-ledger?company_id=3
```

Optional:

```http
GET /reports/general-ledger?company_id=3&start_date=2026-01-01&end_date=2026-01-31
```

---

## Audit Logs

### List audit logs

```http
GET /audit-logs?company_id=3&skip=0&limit=100
```

Requires role:

```text
admin, auditor
```

Optional:

```http
GET /audit-logs?company_id=3&entity_type=journal_entry&entity_id=1
```

Response:

```json
{
  "items": [],
  "total": 0,
  "skip": 0,
  "limit": 100
}
```

---

## Health

### Service health

```http
GET /health
```

### Database health

```http
GET /health/db
```

### Version

```http
GET /health/version
```

---

## Frontend Notes

The frontend should store:

```text
access_token
selected_company_id
current_user
```

Every protected request must send:

```http
Authorization: Bearer <token>
```

List endpoints return paginated responses:

```json
{
  "items": [],
  "total": 0,
  "skip": 0,
  "limit": 100
}
```

Reports return report-specific objects directly.