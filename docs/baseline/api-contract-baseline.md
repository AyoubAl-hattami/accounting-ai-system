# API Contract Baseline

## Contract rule

Future refactors must not change endpoint paths, HTTP methods, request or response
fields, validation behavior, status codes, pagination structure, authentication
requirements, or error behavior unless the change is explicitly approved and
versioned.

The authoritative implementation is currently under
`backend/app/modules/accounting/routes/` and
`backend/app/modules/accounting/schemas/`. OpenAPI at
`http://127.0.0.1:8010/docs` should be captured during an authorized reference
run.

## Health

Defined in `backend/app/api/routes/health.py`:

- `GET /health`
- `GET /health/db`
- `GET /health/version`

## Authentication

Router prefix: `/auth`; implementation:
`backend/app/modules/accounting/routes/auth_routes.py`.

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

Baseline expectations:

- Registration validates the current password policy and normalized identity.
- Login returns the existing bearer-token response structure.
- `/auth/me` requires a valid token and returns the current user contract.
- Invalid or inactive users retain current authentication errors.
- Registration and failed-login rate limits retain current status/error behavior.

Evidence includes `test_password_policy.py`, `test_email_normalization.py`,
`test_rbac_permission_matrix.py`, and authentication portions of other protected
route tests.

## Companies

Router prefix: `/companies`; implementation: `company_routes.py`.

- `POST /companies`
- `GET /companies`
- `GET /companies/{company_id}`
- `PATCH /companies/{company_id}`

List responses must preserve the current pagination envelope and company-scoped
authorization. Evidence: `test_protected_companies.py`,
`test_non_journal_audit_logs.py`, and
`test_non_journal_transaction_atomicity.py`.

## Company users and invitations

Router prefix: `/company-users`; implementation: `company_user_routes.py`.

Important current endpoints:

- `POST /company-users/invitations`
- `GET /company-users/invitations`
- `GET /company-users/invitations/validate`
- `POST /company-users/invitations/accept`
- `DELETE /company-users/invitations/{invitation_id}`
- `GET /company-users/me`
- Company-user create/list/get operations under `/company-users`
- `PATCH /company-users/{company_user_id}`
- `PATCH /company-users/{company_user_id}/remove-access`
- `PATCH /company-users/{company_user_id}/restore-access`
- `PATCH /company-users/users/{user_id}/deactivate`
- `PATCH /company-users/users/{user_id}/reactivate`

The distinction between company membership access and global user activation is
part of the contract. Invitation validation/acceptance query and payload fields,
terminal lifecycle behavior, and current status codes must remain stable.

Evidence: `test_protected_company_users.py`,
`api/test_company_user_invitations.py`,
`test_invitation_lifecycle_integrity.py`,
`test_global_user_admin_authorization.py`, and
`test_rbac_permission_matrix.py`.

## Accounts

Router prefix: `/accounts`; implementation: `account_routes.py`.

- `POST /accounts`
- `GET /accounts`
- `POST /accounts/seed-defaults`
- `GET /accounts/{account_id}`
- `PATCH /accounts/{account_id}`

Contracts include account fields, company ownership, pagination, uniqueness and
validation errors, default-account seeding response, authentication, and audit
behavior. Evidence: `test_protected_accounts.py`,
`test_non_journal_audit_logs.py`, and
`test_non_journal_transaction_atomicity.py`.

## Fiscal years and periods

Implementation: `fiscal_routes.py`.

- `POST /fiscal-years`
- `GET /fiscal-years`
- `GET /fiscal-years/{fiscal_year_id}`
- `PATCH /fiscal-years/{fiscal_year_id}`
- `POST /fiscal-periods`
- `GET /fiscal-periods`
- `GET /fiscal-periods/{fiscal_period_id}`
- `PATCH /fiscal-periods/{fiscal_period_id}`
- `POST /fiscal/quick-setup-today`

Preserve current date formats, status values, pagination, overlap/ownership
validation, error details, and company access rules. Evidence:
`test_protected_fiscal.py`, fiscal control tests, and journal fiscal-enforcement
tests.

## Journal entries

Router prefix: `/journal-entries`; implementation: `journal_routes.py`.

- `POST /journal-entries`
- `POST /journal-entries/opening-balance`
- `GET /journal-entries`
- `GET /journal-entries/{journal_entry_id}`
- `PATCH /journal-entries/{journal_entry_id}`
- `POST /journal-entries/{journal_entry_id}/review`
- `POST /journal-entries/{journal_entry_id}/post`
- `POST /journal-entries/{journal_entry_id}/reverse`
- `POST /journal-entries/{journal_entry_id}/void`

Preserve status names (`draft`, `reviewed`, `posted`, `void`, `reversed`), line
fields, generated identifiers, creator visibility rules, lifecycle conflict
responses, fiscal errors, pagination, and mutation response models.

Evidence: `test_protected_journal_entries.py`,
`test_journal_lifecycle_policy.py`, `test_opening_balance_workflow.py`,
`test_journal_transaction_atomicity.py`, and fiscal control tests.

## Reports and exports

Router prefix: `/reports`; implementations: `report_routes.py`,
`report_export_routes.py`, and `report_pdf_routes.py`.

JSON reports:

- `GET /reports/trial-balance`
- `GET /reports/profit-and-loss`
- `GET /reports/balance-sheet`
- `GET /reports/account-ledger`
- `GET /reports/general-ledger`

CSV exports use:

- `/reports/trial-balance/export.csv`
- `/reports/profit-loss/export.csv`
- `/reports/balance-sheet/export.csv`
- `/reports/account-ledger/export.csv`
- `/reports/general-ledger/export.csv`

PDF exports use the same export paths with `.pdf`.

Note that the JSON profit endpoint uses `profit-and-loss`, while export endpoints
use `profit-loss`. That existing difference is contractual and must not be
"cleaned up" during refactoring.

Preserve date/account query parameters, fiscal errors, report fields, totals,
authentication, content type, filenames, and export content.

Evidence: `test_protected_reports.py`, `test_reports_smoke.py`,
`test_report_csv_exports.py`, and `test_report_pdf_exports.py`.

## Audit logs

Router prefix: `/audit-logs`; implementation: `audit_routes.py`.

- `GET /audit-logs`

Preserve authentication, company scope, pagination, ordering, filters, entity and
action fields, and the absence of invitation secrets. Evidence:
`test_protected_audit_logs.py`, `test_non_journal_audit_logs.py`, transaction
atomicity tests, and `test_invitation_lifecycle_integrity.py`.

## AI and conversations

Router prefix: `/ai`; implementation: `ai_routes.py`.

- `POST /ai/journal-suggestions`
- `GET /ai/status`
- `POST /ai/gemini-assistant`
- `POST /ai/gemini-assistant/confirm-action`

Conversation router prefix: `/ai/conversations`; implementation:
`assistant_conversation_routes.py`.

- `GET /ai/conversations`
- `POST /ai/conversations`
- `GET /ai/conversations/{conversation_id}`
- `PATCH /ai/conversations/{conversation_id}`
- `DELETE /ai/conversations/{conversation_id}`
- `POST /ai/conversations/{conversation_id}/messages`

Preserve provider-status fields, suggestion/reply structures, confidence/source
semantics, grounding, structured confirmation errors, conversation pagination,
message structures, ownership/company scope, and explicit confirmation before
mutation.

Evidence: `test_ai_provider_factory.py`, `test_gemini_assistant.py`,
`test_gemini_assistant_explain.py`, `test_gemini_assistant_profit.py`,
`test_semantic_transaction.py`, and conversation tests.

## Pagination and error baseline

List endpoints that currently use the shared pagination response must retain its
field names and meanings. Refactors must preserve distinctions among validation,
authentication, authorization, not-found, conflict, and server/database errors.
Domain-error extraction is not permission to change current HTTP translation.
