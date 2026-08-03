# Phase 69 — Product Readiness Audit

Date: 2026-08-02
Scope: Documentation-only audit. No runtime, schema, auth, or RBAC changes were made.
Audience: Product/engineering leadership deciding what Phase 70+ should build.

---

## 1. Executive Summary

The repository contains a genuinely well-architected **general ledger core** (chart of
accounts, journal entries, fiscal years/periods, trial balance / P&L / balance sheet /
ledger reports, audit log, AI journal-suggestion assistant) with clean-architecture
layering (`backend/app/application` use cases + ports, `backend/app/infrastructure`
adapters, `backend/app/modules/accounting` routes/schemas/services) and a genuinely
large automated test suite (554 `def test_*` functions across 77 files in
`backend/tests`). CI runs on every PR (`.github/workflows/backend-validation.yml`,
`.github/workflows/frontend-validation.yml`).

What it is **not** yet: an accounting product a real business can run its books on.
There are no invoices, no customers/suppliers (accounts receivable/payable), no
payments, no bank accounts or bank reconciliation, no VAT/tax handling, no
attachments/document storage, no fiscal period lock, no multi-currency support beyond
a single `base_currency` string per company, and no deployment artifacts (no
Dockerfile, no docker-compose, no CI deploy step) anywhere in the repo.

In short: the **debit/credit engine and reporting layer are demo-ready and close to
production-ready in isolation**, but the product currently only supports manually
entered journal entries — it has no transactional subledgers (AR/AP/bank), which is
what a real accounting product is judged on. Phase 70+ should treat this as "the
ledger kernel is done — now build the subledgers on top of it."

---

## 2. What Works Today (evidence-based)

- **Authentication** — register/login/`/auth/me`, JWT via `app/infrastructure/auth/token_service.py`,
  rate limiting on login and (optionally) registration
  (`backend/app/modules/accounting/routes/auth_routes.py`), audit logging of
  `login_success` / `login_failure` / `register_user`. Password policy has its own
  test file (`backend/tests/test_password_policy.py`).
- **Multi-company / tenant scoping** — `backend/app/application/companies`,
  `company_access.py` (`ensure_company_access`), `company_user_routes.py`, role-based
  permission checks used in routes (`AuditLogsPage`/`CompanyUsersPage`/`SettingsPage`
  are gated with `requiredPagePath` in `frontend/src/routes/AppRoutes.tsx`), invitation
  lifecycle (`backend/app/application/invitations`,
  `frontend/src/features/company-users/AcceptInvitePage.tsx`). Dedicated tests:
  `test_rbac_permission_matrix.py`, `test_protected_company_users.py`,
  `test_global_user_admin_authorization.py`, `test_invitation_lifecycle_integrity.py`.
- **Chart of accounts** — CRUD with hierarchy (`parent_id` self-FK,
  `backend/app/modules/accounting/models/account.py`), system/protected accounts that
  block deletion/mutation of protected fields (`account_routes.py:62,260-278`,
  `test_protected_accounts.py`), default COA seeding
  (`backend/app/application/accounts/defaults.py`).
- **Journal entries** — full draft → reviewed → posted → void/reverse lifecycle
  (`backend/app/application/journals/use_cases.py`,
  `backend/app/modules/accounting/routes/journal_routes.py`), double-entry balance
  validation, opening balances (`CreateOpeningBalanceCommand`), transaction atomicity
  tests (`test_journal_transaction_atomicity.py`,
  `test_non_journal_transaction_atomicity.py`), 10+ dedicated journal use-case/
  repository test files.
- **Reports** — trial balance, P&L, balance sheet, account ledger, general ledger, all
  with CSV export (`backend/app/infrastructure/exports/csv_renderer.py`,
  `report_export_routes.py`) and PDF export (`pdf_renderer.py`,
  `report_pdf_routes.py`), each with its own frontend page under
  `frontend/src/features/reports/**`, matched by
  `test_report_csv_exports.py`, `test_report_pdf_exports.py`, `test_reports_smoke.py`.
- **Audit trail** — `prepare_audit_log` / `create_audit_log` are called from auth,
  journal, and other mutation routes; a dedicated `AuditLogsPage.tsx` +
  `AuditActionBadge.tsx` + `AuditDetailsPanel.tsx` render it; protected/immutable audit
  log tests exist (`test_protected_audit_logs.py`, `test_non_journal_audit_logs.py`).
- **AI accounting assistant** — a provider-abstraction (`ai_provider_factory.py`) with
  `rules` (always-available, deterministic), `llm_placeholder`, `openai`, `gemini`
  providers, and **guaranteed fallback to `rules` on any failure** (see
  `get_journal_suggestion_provider()` docstring/try-except in
  `backend/app/modules/accounting/services/ai_provider_factory.py`). There is also a
  richer "Gemini Assistant" conversational surface
  (`ai_routes.py`, `assistant_conversation_routes.py`,
  `gemini_assistant_service.py`, `assistant_intent_orchestrator.py`) with grounding
  tests for trial balance, P&L, balance sheet, and ledger
  (`test_assistant_*_grounding.py`). Frontend surfaces:
  `GlobalGeminiAssistant.tsx`, `GeminiAssistantPanel.tsx`, `GroundingCards.tsx`,
  `JournalAssistantPanel.tsx`.
- **Frontend shell** — React Router with lazy-loaded routes and a `ProtectedRoute`
  wrapper (`frontend/src/routes/AppRoutes.tsx`), i18n scaffolding for ar/en
  (`frontend/src/i18n/index.tsx`, `translations.ts`, `types.ts`), loading/error/empty
  state components (`frontend/src/components/feedback/`), a dashboard with charts
  (`frontend/src/features/dashboard/DashboardPage.tsx`, uses `recharts`).
- **Testing & CI** — 554 backend test functions in 77 files; frontend has
  `frontend/tests/architecture_guard.test.mjs` and `pendingContext.test.mjs` plus a
  `vitest.config.ts` and `test/smoke` directory; two GitHub Actions workflows run
  static validation (type-check, lint) on every PR/push to main
  (`.github/workflows/backend-validation.yml`,
  `.github/workflows/frontend-validation.yml`).

---

## 3. What's Partial

- **Multi-currency** — `Company.base_currency` (`backend/app/modules/accounting/models/company.py:20`)
  is a single 3-char string per company. There is no FX rate table, no per-transaction
  currency, no conversion logic anywhere in `backend/app/application` or
  `backend/app/modules/accounting/models`. Reports display one currency only.
- **Fiscal period lock / close** — `FiscalPeriodDTO`/`FiscalYearDTO` carry a `status`
  field (`backend/app/application/fiscal/dto.py`) and there is a
  `test_fiscal_year_date_protection.py`, but there is no evidence of a hard "period is
  closed, journal posting must be blocked" enforcement path being exercised beyond
  date-range validation — this needs verification before being called a real close
  process; it should be treated as *not yet a full fiscal close workflow*.
- **AI assistant safety** — rules-based fallback is solid and demo-safe, but the LLM
  paths (`openai_provider.py`, `gemini_provider.py`) depend on external API keys not
  present in `.env.example` by default (empty strings) — acceptable for demo (falls
  back to rules) but the LLM-path behavior under production load, cost, and prompt
  injection has not been audited here.
- **i18n** — infrastructure exists (`frontend/src/i18n/*`) and is wired into pages
  (e.g., `DashboardPage.tsx` uses `useI18n()`), but coverage across all
  components/errors was not exhaustively verified in this audit; likely has gaps in
  toast/error messages.
- **Reporting date filters / currency display** — reports exist and export, but true
  configurability (custom date ranges vs fixed periods, multi-currency display) was
  not confirmed line-by-line for every report page in this pass — recommend a
  dedicated QA pass in Phase 70.

---

## 4. What's Missing (major product gaps)

None of the following have any matching route, model, service, or frontend feature in
the repo (`grep -ril "invoice|customer|supplier|vendor|bank" backend/app frontend/src`
returned **zero** matches in either backend or frontend product code — only AI-prompt
strings that mention "invoice" as a generic accounting term inside
`gemini_transaction_parser.py` / `account_mapper.py`, not an actual invoice feature):

- Sales invoices / accounts receivable
- Purchase bills / accounts payable
- Customers and suppliers as first-class entities
- Payments (customer receipts, supplier payments)
- Bank accounts and bank transactions
- Bank reconciliation
- VAT/tax configuration and calculation
- Attachments / document storage on any transaction
- Document numbering sequences (invoice/bill numbers) — journal entries do have a
  no. field, but no cross-document numbering sequence framework exists
- Multi-currency conversion
- CSV/data import (only export exists)
- Recurring journal entries
- Approval workflows beyond the draft/reviewed/posted journal states
- Company settings beyond fiscal + basic company profile
- Email sending (invoices, reports, invitations are presumably link-based only)
- Backup/restore tooling or UI
- **Deployment artifacts** — no `Dockerfile`, no `docker-compose.yml`, no deploy step
  in either CI workflow anywhere in the repo tree (confirmed via
  `find . -iname "Dockerfile*" -o -iname "docker-compose*"` returning nothing outside
  `node_modules`).

---

## 5. Demo Blockers (top 5)

> **Status update 2026-08-03 (Phase 71).** Blocker 1 is resolved
> (`backend/scripts/seed_demo_data.py`). Blocker 2 is resolved for local
> development via `scripts/dev-*.ps1` plus `docs/demo/local-demo-quickstart.md`;
> Docker Compose is still absent and now sits with Phase 75. Blocker 3 is
> documented rather than removed — the demo path defaults to the offline `rules`
> provider and the quickstart explains how to switch. Blockers 4 and 5 are open.

1. **No sample/seed data story beyond default COA** — a demo needs a company with
   realistic transaction history; `backend/app/application/accounts/defaults.py`
   seeds a chart of accounts but there's no seeded set of journal entries/reports to
   show a compelling "this is a working ledger" demo out of the box.
2. **No Docker/one-command local run** — `README.md` describes manual Postgres +
   `alembic` + `uvicorn` + `npm run dev` setup; a demo audience (or a new engineer)
   has no `docker-compose up` path. This is the single biggest friction point for any
   external demo.
3. **AI assistant demo path depends on unset API keys** — `GEMINI_API_KEY` and
   `OPENAI_API_KEY` are empty by default (`backend/.env.example`); the AI features
   silently fall back to the `rules` provider, which is safe but means the flashiest
   feature (Gemini conversational assistant) shows degraded behavior unless a real key
   is configured before the demo.
4. **No invoices/customers to show a full business cycle** — a prospective demo
   audience for "accounting software" will expect to create a customer, send an
   invoice, and record a payment. Today the demo can only show manual journal entries
   and reports, which reads as a bookkeeping ledger, not a product.
5. **Dashboard/report currency and empty states unverified end-to-end** — with no
   seed data, first-run screens (dashboard KPIs, reports) will show only empty/zero
   states; `LoadingState`/`ErrorState` components exist
   (`frontend/src/components/feedback/`) but the "empty state" first impression was
   not manually walked through in this audit and should be checked before any demo.

## 6. Production Blockers (top 5)

1. **No deployment pipeline** — zero Dockerfiles, zero docker-compose, no CD step in
   either `.github/workflows/*.yml` (both are validation-only: type-check/lint/tests).
   There is currently no repeatable way to build and ship this to any environment.
2. **No fiscal period lock enforcement confirmed** — without a verified hard block on
   posting into a closed period, financial data integrity for real bookkeeping is at
   risk; `backend/app/application/fiscal` needs an explicit audited "period closed →
   reject posting" path before production use.
3. **Missing core subledgers (AR/AP, bank)** — a production accounting system without
   invoices, bills, customers/suppliers, or bank reconciliation cannot be used to run
   a real business's books; this is a functional-completeness blocker, not a
   code-quality one.
4. **No backup/restore tooling** — no scripts, docs, or UI found for database
   backup/restore; for a production financial system this is a compliance and
   operational-risk gap.
5. **Secrets/config hygiene not verified for production** — `backend/.env` exists in
   the working tree (alongside `.env.example`); the audit did not verify
   `.env` is gitignored in this pass. **Recommendation: verify `backend/.env` and
   `frontend/.env` are excluded via `.gitignore` before any production or public
   repository work** — this needs an explicit check as part of Phase 70/75, since
   committed secrets would be a severe production blocker.

---

## 7. Readiness Scores (0–5, strict)

| Area | Score | Reason | Strongest evidence | Main blocker | Next action |
|---|---|---|---|---|---|
| Architecture readiness | 4 | Clean separation of application/use-cases, infrastructure adapters, and route/schema/service layers; ports+DTOs pattern is consistently applied | `backend/app/application/*/ports.py`, `use_cases.py`, `backend/app/infrastructure/database/sqlalchemy/repositories/*` | Some legacy `modules/accounting/services` still mix concerns with routes | Continue migrating remaining `modules/accounting/services` logic into `application` use cases as new features are added |
| Backend API readiness | 3.5 | Ledger, reports, auth, fiscal, audit are complete and tested; no AR/AP/bank/tax APIs exist at all | `backend/app/modules/accounting/routes/*.py` (12 route files, none for invoices/customers/payments) | Missing subledger APIs | Design invoice/customer/payment API surface in Phase 71 |
| Frontend UI readiness | 3 | 9 real feature pages wired into routing with protected routes, i18n, loading/error states; no invoice/customer/payment screens exist | `frontend/src/routes/AppRoutes.tsx` (9 protected routes) | No UI for missing subledgers; empty-state UX not verified | Build subledger pages once backend APIs land; do a manual empty-state walkthrough |
| Accounting completeness | 2 | Core GL (COA, journals, fiscal periods, reports) is real and tested, but a business cannot invoice, bill, pay, or reconcile a bank account | Zero invoice/customer/supplier/bank matches across backend+frontend (grep) | No AR/AP/bank/tax | This is the core Phase 71–73 roadmap |
| Security/auth readiness | 3.5 | JWT auth, rate limiting on login/registration, audit logging of auth events, password policy tests | `auth_routes.py`, `test_auth_rate_limit.py`, `test_password_policy.py` | LLM prompt-injection / API-key handling not audited; `.env` gitignore status not verified in this pass | Verify `.env` exclusion; security-review the AI assistant input path before Phase 76 |
| Tenant/RBAC readiness | 4 | Company-scoped access checks, invitations, role-based route gating on frontend, dedicated permission-matrix tests | `ensure_company_access`, `test_rbac_permission_matrix.py`, `requiredPagePath` gating in `AppRoutes.tsx` | Coverage depth of permission matrix vs. every new subledger not yet applicable | Extend RBAC to new resources as subledgers are added |
| Reporting readiness | 4 | 5 core reports (TB, P&L, BS, account ledger, GL) with CSV+PDF export, each with dedicated page and tests | `report_routes.py`, `report_export_routes.py`, `report_pdf_routes.py`, 3 report test files | No AR/AP aging or bank reports (don't exist yet because AR/AP doesn't exist) | Add AR/AP aging once subledgers exist |
| AI readiness | 3.5 | Provider abstraction with safe rules-fallback, grounding tests for 4 report types, conversational assistant with confirm-action flow | `ai_provider_factory.py` fallback logic, `test_assistant_*_grounding.py` (4 files) | LLM provider production hardening (cost/rate-limit/injection) not audited | Dedicated AI security/cost review in Phase 76 |
| Testing readiness | 4 | 554 backend test functions across 77 files covering use cases, repositories, protected-resource behavior, transaction atomicity | `backend/tests/` file listing | Frontend test coverage is thin (4 test files vs. 27+ feature components) | Expand frontend component/integration tests in Phase 70 |
| CI/deployment readiness | 1.5 | CI runs type-check/lint/tests on PR; there is no build/deploy pipeline and no containerization anywhere in the repo | `.github/workflows/backend-validation.yml`, `.github/workflows/frontend-validation.yml` (both validation-only); zero Dockerfiles found | No CD, no Docker, no deploy target | Phase 75: containerize + define a deploy target |
| Documentation readiness | 3.5 | Extensive architecture docs (`docs/architecture/*`), baseline docs (`docs/baseline/*`), API checklist (`BACKEND_API_CHECKLIST.md`) | `docs/architecture/` (12 files), `docs/baseline/` (7 files) | No product/business-facing docs before this audit; no deployment runbook | This audit adds `docs/product/*`; add a deployment runbook in Phase 75 |
| Production readiness | 1.5 | Solid core engine but missing deployment pipeline, unverified fiscal lock, unverified secrets hygiene, and no subledgers means it cannot run a real business's books | See Production Blockers above | Combination of missing deploy pipeline + missing subledgers | Sequence Phase 70 (demo) → 71–74 (subledgers) → 75 (deploy hardening) |

**Overall assessment: this is a strong, well-tested accounting *engine*, not yet an
accounting *product*.**

---

## 8. Accounting Gap Analysis (summary — see companion doc for full table)

See `docs/product/accounting-feature-gap-analysis.md` for the full
status/evidence/business-impact/phase table. Headline: every Must-have transactional
subledger (invoices, bills, customers, suppliers, payments, bank
accounts/transactions, bank reconciliation, VAT/tax) is **missing**; the GL kernel
underneath them (accounts, journals, fiscal periods, audit trail) is **present and
tested**, which is exactly the right foundation to build subledgers on top of.

---

## 9. Security / Deployment Gap Analysis

- **Auth**: present and reasonably hardened for an MVP (rate limiting, audit logging,
  password policy tests) — see `backend/app/modules/accounting/routes/auth_routes.py`.
- **Secrets**: `.env.example` files exist for both backend and frontend with sane
  defaults (e.g., `SECRET_KEY=replace-with-a-secure-random-secret` explicitly flagged
  as needing replacement); actual `backend/.env` and `frontend/.env` files exist in
  the working tree — **verify these are gitignored and never committed** before any
  production work; this audit did not modify or inspect their contents.
- **Deployment**: no Dockerfile, no docker-compose, no CD workflow step, no documented
  production deployment target (cloud provider, process manager, reverse proxy) found
  anywhere in the repo. `README.md` documents local dev setup only.
- **Backup/restore**: no scripts or docs found under `scripts/` or `docs/` addressing
  database backup/restore procedures.
- **Rate limiting**: present for login/register only (`app/core/rate_limit.py` used in
  `auth_routes.py`); not evaluated for other mutation-heavy endpoints (journal
  posting, report generation) in this pass — out of scope per hard constraints (no
  rate-limiting changes), but worth a Phase 75 review.

---

## 10. Recommended Roadmap (Phase 70+)

See `docs/product/phase-70-demo-readiness-plan.md` for the fully detailed Phase 70
plan. Summary of the full roadmap:

| Phase | Goal | Primary risk |
|---|---|---|
| 70 | Demo readiness: seed data, Docker Compose for local demo, verify empty/loading states, verify `.env` hygiene, README/demo script | Low — additive only |
| 71 | Invoices/customers/suppliers foundation (AR/AP master data + document CRUD, no payments yet) | Medium — new domain, needs its own ports/use-cases/migrations |
| 72 | Payments and bank transactions (link payments to invoices/bills, basic bank transaction entry) | Medium — touches journal-posting integration |
| 73 | VAT/tax and fiscal controls (tax codes, tax on invoices/bills, real fiscal period lock enforcement) | Medium-High — affects posting rules |
| 74 | Attachments/PDF/export polish (invoice PDF templates, document attachments, email sending) | Low-Medium |
| 75 | Production deployment hardening (Docker, CI/CD, backup/restore, secrets audit) | Medium — infra work, not app logic |
| 76 | AI accounting assistant production hardening (cost controls, prompt-injection review, LLM provider SLAs) | Medium — security-sensitive |

Each phase is detailed with scope/files/risk/validation in the phase plan doc for
Phase 70; Phases 71–76 should each get their own such plan document when they start.
