# Regression Risk Map

Use this map to select focused verification before and after each refactor.

## Journal lifecycle — Very high

**What could break**

- Unbalanced entries accepted.
- Illegal draft/review/post/void/reverse transitions.
- Posted entries becoming editable.
- Duplicate or incorrect reversals.
- Wrong account/company association or fiscal period.
- Changed status codes or journal response fields.

**How to verify**

- Focused lifecycle, fiscal, opening-balance, protected-route, and atomicity
  tests.
- Compare ledger/report effects before and after.
- Manually exercise each action on disposable entries.

**Inspect**

- Journal routes, application use cases, SQLAlchemy journal repository, and
  journal schemas/models.
- `test_journal_lifecycle_policy.py`
- `test_journal_transaction_atomicity.py`
- `test_opening_balance_workflow.py`
- `test_protected_journal_entries.py`
- `accounting-domain-baseline.md`

## Report calculations — Very high

**What could break**

- Draft/void/reversed entries included incorrectly.
- Debit/credit signs or account classifications changed.
- Fiscal/date boundaries drift.
- JSON, CSV, and PDF totals disagree.
- Cross-company entries appear.

**How to verify**

- Reconcile exact fixture results for all five reports.
- Compare JSON, CSV, and PDF outputs.
- Verify balanced trial balance and report-specific totals.

**Inspect**

- Report application use cases and repository, report routes/schemas, and
  CSV/PDF services.
- `test_reports_smoke.py`
- `test_protected_reports.py`
- `test_report_csv_exports.py`
- `test_report_pdf_exports.py`
- `accounting-domain-baseline.md`

## Transaction boundaries — Very high

**What could break**

- Service flush without an eventual commit.
- Early commit before validation or audit.
- Returned success for rolled-back data.
- Session unusable after an integrity failure.
- Duplicate commits or audit records.

**How to verify**

- Execute focused rollback tests and full suite.
- Inject audit failure into every changed mutation.
- Confirm generated IDs/response data remain available.

**Inspect**

- `core/database.py`, `audit_service.py`, all mutating routes/services.
- `test_journal_transaction_atomicity.py`
- `test_non_journal_transaction_atomicity.py`
- `transaction-and-audit-baseline.md`

## Audit atomicity — Very high

**What could break**

- Mutation commits without required audit.
- Success audit survives failed mutation.
- Wrong company/global scope.
- Duplicate events or exposed secrets.

**How to verify**

- Audit-failure rollback tests.
- Successful operation produces exactly one expected event.
- Audit listing scope/filter checks and secret inspection.

**Inspect**

- `audit_service.py`, `audit_routes.py`, mutation routes.
- `test_non_journal_audit_logs.py`
- `test_protected_audit_logs.py`
- Transaction and invitation atomicity tests.

## RBAC and company isolation — Very high

**What could break**

- Viewer gains mutation access.
- Company admin affects another company.
- Superuser bypass loses explicit company scope.
- Inactive user retains access with an old token.
- Hidden resources leak through changed 403/404 behavior.

**How to verify**

- Run RBAC matrix and every affected protected-route test.
- Exercise admin, viewer, superuser, inactive, and cross-company cases.

**Inspect**

- `auth_dependencies.py`, `company_access.py`, protected routes.
- `test_rbac_permission_matrix.py`
- `test_protected_company_users.py`
- `test_global_user_admin_authorization.py`
- `rbac-and-security-baseline.md`

## Invitations — High

**What could break**

- Duplicate live invitations.
- Normalization mismatch.
- Expired/cancelled token accepted.
- Double acceptance or destructive reissue.
- Secret token/hash in audit logs.
- Concurrent terminal actions both succeed.

**How to verify**

- Invitation API, lifecycle, concurrency, and audit-failure tests.
- Verify same normalized email behavior within and across companies.

**Inspect**

- Invitation model/schema/service/routes and lifecycle migration.
- `test_invitation_lifecycle_integrity.py`
- `api/test_company_user_invitations.py`
- `rbac-and-security-baseline.md`

## AI assistant confirmation — Very high

**What could break**

- Preview creates a journal entry.
- Model output bypasses permissions or fiscal rules.
- Viewer confirms a mutation.
- Failure leaves a partial entry.
- Provider output invents account IDs or amounts.

**How to verify**

- Provider validation/fallback tests.
- Preview versus confirm tests.
- Fiscal, viewer, date, audit, failure, grounding, and isolation cases.

**Inspect**

- `ai_routes.py`, provider factory/adapters, intent orchestrator,
  `gemini_assistant_service.py`.
- `test_ai_provider_factory.py`
- `test_gemini_assistant.py`
- `test_semantic_transaction.py`
- `ai-baseline.md`

## Theme and RTL — High

**What could break**

- Low contrast or unreadable financial data.
- Dark-mode surface/text mismatch.
- Arabic actions overlap or order incorrectly.
- Tables, modals, assistant bubbles, or navigation overflow.
- Chart colors lose meaning.

**How to verify**

- Manual light/dark and English/Arabic pass on every major route.
- Desktop/mobile widths and keyboard focus.
- Compare screenshots for high-density pages.

**Inspect**

- `styles/globals.css`, Tailwind config, `AppShell.tsx`, report and journal
  pages, company users, settings, AI panels.
- `frontend-baseline.md`
- `docs/architecture/theme-architecture.md`

## Frontend route preservation — High

**What could break**

- URL renamed during page moves.
- Protected route becomes public.
- Root/unknown redirect changes.
- Lazy import or navigation link breaks.
- Permission-filtered navigation disagrees with route protection.

**How to verify**

- Visit every URL directly, refresh, navigate through the shell, and test
  unauthenticated/unauthorized access.

**Inspect**

- `frontend/src/routes/AppRoutes.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend-baseline.md`

## Migrations and Alembic — Very high

**What could break**

- Model moves remove metadata from autogeneration/runtime imports.
- Multiple heads or wrong revision ancestry.
- Existing schema no longer upgrades.
- Downgrade destroys important data.
- Repository mapping diverges from database constraints.

**How to verify**

- `alembic current`, `alembic heads`, and `alembic upgrade head` on approved
  PostgreSQL.
- Downgrade/upgrade only on a disposable database.
- Compare model metadata, constraints, and migration history.

**Inspect**

- `backend/alembic/`
- SQLAlchemy models and database initialization.
- `verification-commands.md`
- `docs/architecture/backend-target-architecture.md`

## API contract drift — High

**What could break**

- Path/method, payload, field, pagination, status, or error changes.
- Profit-and-loss JSON/export path differences accidentally normalized.
- Domain errors translated differently after use-case extraction.

**How to verify**

- Compare OpenAPI snapshots and representative endpoint responses.
- Run affected contract/protected tests.

**Inspect**

- Route and schema files.
- `api-contract-baseline.md`

## Risk acceptance rule

An architecture commit is not complete while an applicable very-high or high
risk lacks an executed verification result. Environmental inability to verify is
a documented blocker, not a pass.
