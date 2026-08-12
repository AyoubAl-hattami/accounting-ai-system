# Production readiness audit

Audit date: 2026-08-12

Baseline: `main` at `5bacfa4`, tag `stable-local-demo-cleanup-final-2026-08-12`

Target: first paying customer, production v1

## Executive summary

The product has a credible application core. Authentication uses bcrypt and
signed JWTs; temporary credentials are hashed and force a password change;
tenant access is checked before subscription state; platform administrators are
kept out of tenant routes; accounting records have useful database constraints;
AI conversations are scoped to company, user, and conversation; PostgreSQL has
one current Alembic head; CI validates migrations and the full backend and
frontend suites; and the frontend TypeScript and production build complete.

The system is **not ready to accept a real paying customer yet**. The remaining
work is concentrated around the production perimeter and operating model, not a
large product redesign. Six critical launch blockers must be closed: public
identity enrollment, production session security, platform-owner bootstrap and
recovery, a reproducible HTTPS deployment, tested backup/restore plus monitoring,
and legal/data-governance terms. Product scope must also be stated honestly: this
is a double-entry ledger and reporting product, not yet a complete statutory tax,
invoicing, payroll, attachment, or bank-reconciliation suite.

## Decision

**NO-GO for production v1 and customer handover.**

Phase 77B implements repository-level controls for registration, token TTL and
password-change invalidation, platform-owner bootstrap, fail-closed production
configuration and subscriptions, deployment templates, and operating runbooks.
The decision remains NO-GO until the external evidence in the final production
gate exists. See the Phase 77B status table below.

### Phase 77B blocker status

| Blocker | Repository status | Remaining GO evidence |
|---|---|---|
| C1 public registration | Code control complete | Staging test showing production returns 404 and onboarding still works |
| C2 session security | Partially complete | HttpOnly/revocable session decision, platform MFA, CSP verification, security sign-off |
| C3 owner bootstrap | Code control complete | Witnessed production bootstrap and break-glass owner assignment |
| C4 deployment/HTTPS | Templates complete, external pending | Real DNS/TLS/hosting/secrets, staging deployment and rollback evidence |
| C5 recovery/monitoring | Runbooks complete, external pending | Successful restore drill meeting approved RPO/RTO and alert evidence |
| C6 legal/governance | Checklist complete, external pending | Counsel/business-approved documents and customer acceptance |

The application may continue to be demonstrated locally. A limited production
pilot becomes a GO only after all critical blockers below are implemented,
tested in a production-like environment, and signed off by the accountable
business owner. High-priority items marked "before pilot" are also release gates.

## Evidence reviewed

- FastAPI configuration, authentication, password-change gate, tenant access,
  subscription access, platform routes, onboarding, rate limiting, and health
  endpoints.
- SQLAlchemy models, all 16 Alembic revisions, PostgreSQL migration state,
  database constraints, indexes, and transaction boundaries.
- React authentication context, route guards, company selection, API base URL,
  platform dashboard, onboarding, subscriptions, and production build.
- Demo seed, cleanup, onboarding, subscription-management, tunnel, CI, and local
  development scripts.
- Current product, architecture, demo, handover, subscription, and accounting
  gap documentation.

Validation observed during this audit:

- Alembic reports exactly one head: `c9d4b7e2f813`.
- The local PostgreSQL database is at Phase 77B head `e2a7f6c1d904`.
- Frontend `npx tsc -b --noEmit` passed.
- Frontend production build passed with Vite 5.4.21; temporary output was removed.
- CI is configured to migrate a fresh PostgreSQL 16 service and run the complete
  backend suite; frontend CI runs type checking, lint, build, architecture guard,
  and Vitest.

## Critical blockers

### C1. Public account registration was enabled in production

Phase 77B makes production registration disabled by default and rejects startup
if it is explicitly enabled. `POST /auth/register` returns 404 while platform
onboarding remains available. Non-production registration remains configurable.

**Repository control:** complete. Production registration is closed and covered
by configuration and route tests. Staging evidence remains required.

### C2. Production session security is insufficient for financial data

Phase 77B requires an explicit production TTL, rejects more than 60 minutes
without documented risk acceptance, and adds a database token version. Password
change, deactivation, and reactivation invalidate all previously issued tokens;
the frontend obtains a fresh token after password change. The SPA still stores
the bearer token in `localStorage`; there is no refresh rotation, general session
revocation UI, or platform-admin MFA.

**Required before pilot:** use short-lived access tokens and a secure session
strategy with revocation/rotation. Prefer an `HttpOnly`, `Secure`, `SameSite`
cookie architecture, or document and test an equivalently strong design. Revoke
all outstanding sessions on password change, deactivation, and credential reset.
Add CSP and security headers at the serving layer. Require MFA for platform
administrators, or record explicit risk acceptance for a tightly controlled
single-customer pilot.

### C3. Platform-owner bootstrap needs operational evidence

Phase 77B adds a confirmed, idempotent, audited bootstrap CLI that rejects demo
credentials, forces password change, and requires explicit promotion of an
existing user. `backend/restore_admin.py` now refuses production execution.

**Repository control:** complete. A witnessed production execution, named
break-glass owners, and secure one-time credential delivery remain required.

### C4. Deployment templates exist; real HTTPS deployment is unproven

Phase 77B adds backend/frontend Dockerfiles, internal Nginx SPA/API routing,
Caddy HTTPS/HSTS configuration, an example Compose topology, a deployment
runbook, same-origin production API defaults, and fail-closed backend settings.
No real DNS, certificates, hosting, secret manager, or staging deployment has
been provisioned or verified, so C4 remains externally pending.

**Repository control:** complete as a reference template. A staging deployment
must prove DNS, TLS renewal, trusted proxies, security headers, `/api` routing,
SPA fallback, secret injection, worker behavior, and rollback. Cloudflare Quick
Tunnel and Vite dev server are never production deployment options.

### C5. No tested backup, restore, monitoring, or incident recovery

Phase 77B defines backup/restore, reconciliation, monitoring, incident, migration,
and deployment rollback runbooks. There is still no configured backup provider,
approved retention/RPO/RTO, successful restore drill, alert delivery evidence,
centralized logging/error tracking, or practiced infrastructure rollback.

**Required before pilot:** define RPO/RTO; automate encrypted backups; restore a
backup into an isolated environment and reconcile row/report checks; monitor
availability, database capacity, failed logins, 5xx rates, migration failures,
subscription jobs, and backup success; define on-call ownership and an incident
communication path; document application and migration rollback.

### C6. Legal, privacy, and accounting-service terms are absent

There are no customer Terms of Service, Privacy Notice, data-processing terms,
retention/deletion policy, subprocessor disclosure for AI providers, breach
process, support commitment, or accounting reliance disclaimer. Jurisdiction,
data residency, tax obligations, and controller/processor responsibilities are
undefined. The product itself documents missing tax/VAT, attachments, invoice,
bank reconciliation, payroll, and broader statutory workflows.

**Required before pilot:** obtain jurisdiction-specific legal review; publish and
accept the applicable terms; disclose hosting and AI subprocessors; define data
retention/export/deletion; state that AI output requires human review; state the
supported accounting scope and excluded statutory/tax functions; define support,
billing, suspension, cancellation, renewal, refund, and data-exit policies.

**Critical blocker count: 6.**

## High-priority blockers

These must be closed before the pilot unless the item is explicitly accepted in
a written, time-bounded risk register.

1. **Production configuration validation (code complete).** Startup now requires
   HTTPS `APP_PUBLIC_URL`, exact HTTPS CORS, PostgreSQL, bounded explicit token
   TTL, strong secrets, approved AI configuration, and fail-closed subscriptions.
2. **Distributed rate limiting.** Replace process-memory counters with a shared
   store or edge/WAF limits. Honor forwarded client IP only from trusted proxies.
   Cover login, registration/invitation acceptance, AI, exports, and expensive
   report endpoints.
3. **Password recovery and administrator MFA.** There is no user-facing reset
   flow. Build a time-limited, single-use, hashed reset-token workflow with audit
   events and avoid support staff handling customer passwords.
4. **Subscription fail-open behavior (code complete).** A production company
   without a subscription row is now blocked as unmanaged; non-production legacy
   behavior remains compatible. Reconcile rows and monitor anomalies before launch.
5. **API information and error policy (partial).** `/health/version` no longer
   exposes environment in production. Some report routes return domain exception
   messages. Define a
   stable error envelope, log correlation ID, generic 5xx responses, and a policy
   for public health metadata and API documentation exposure.
6. **Secrets and dependency operations.** Use a secret manager, rotation process,
   least-privilege database role, lockfile-based deploy, dependency/SBOM scanning,
   and scheduled patching. CI currently has no dependency vulnerability gate.
7. **AI privacy decision.** Decide whether production v1 uses `rules`, Gemini, or
   OpenAI. For external providers, approve terms, residency, retention, and
   customer disclosure; verify no secrets are logged; provide a tenant-level
   disable option or contractual limitation before transmitting accounting text.
8. **Production data initialization.** Start from a new production database.
   Never copy the local database. Do not run demo seed, cleanup, reset, tunnel,
   or hard-coded repair scripts. Verify zero demo identities and companies.

## Medium-priority improvements

- Increase password minimum length and consider breached-password screening;
  retain current uppercase/lowercase/digit checks only as one layer.
- Add explicit database connection pool, timeout, recycling, and statement-timeout
  configuration suitable for the chosen service size.
- Add request IDs, JSON logs, audit-log export/retention, and redaction tests.
- Add readiness and liveness semantics separately; database health should have a
  strict timeout and should not expose internal errors.
- Add production E2E tests for login, forced password change, platform onboarding,
  tenant isolation, subscription lockout, journal lifecycle, and all reports.
- Run performance/load tests for large ledgers, exports, platform pagination, and
  concurrent posting. Define maximum supported tenant/user/entry volumes.
- Review database indexes using production-like `EXPLAIN ANALYZE`; current foreign
  keys and common scope columns are generally indexed, but no workload study exists.
- Define fiscal close/reopen governance, audit export, record retention, and
  correction procedures with a qualified accountant for the target jurisdiction.
- Add customer data export and account/company deletion workflows consistent
  with retention law and accounting immutability requirements.
- Add accessibility and browser/device acceptance testing beyond component smoke
  tests; retain the current responsive, RTL, and theme coverage.

## Low-priority improvements

- Reduce the largest frontend chunks and set performance budgets.
- Make API docs availability configurable by environment.
- Add a branded maintenance page and customer-facing service-status page.
- Add automated release notes and deployment provenance/version display for support.
- Remove or quarantine legacy local repair scripts after a supported replacement
  exists, especially `backend/restore_admin.py`.
- Expand localized operational/error copy and customer documentation.

## Existing strengths

### Security and SaaS boundaries

- Passwords are bcrypt-hashed; plaintext temporary passwords are returned once
  and are not stored or written to audit logs.
- Password policy requires at least eight characters with lowercase, uppercase,
  and a digit; password reuse against the current password is rejected.
- `must_change_password` is enforced centrally for authenticated routes, with
  only `/auth/me` and `/auth/change-temporary-password` allowed.
- Company membership is checked before subscription state, limiting tenant
  existence/status leakage. Platform superusers are rejected from tenant routes.
- Platform dashboard, subscriptions, and onboarding use the dedicated
  `get_current_platform_admin` dependency.
- Client onboarding creates company, client admin, membership, subscription,
  optional chart, and fiscal calendar in one transaction. The platform admin is
  not added to the tenant.
- AI conversations are queried by company and user ownership; recent provider
  history is bounded. The assistant proposes drafts and does not post entries.

### Database and accounting

- One linear Alembic head exists and CI exercises a fresh PostgreSQL 16 database.
- Tenant keys, statuses, account types, debit/credit shape, fiscal ranges, journal
  transitions, invitation lifecycle, and reversal uniqueness have constraints.
- Posted-entry correction uses reversal rather than direct mutation.
- Reports classify by account type, supporting custom account names and nullable
  account subtypes.

### Frontend

- Production TypeScript/build validation passes and routes are lazy-loaded.
- Platform administrators land in the platform control plane and stale tenant
  company selection is cleared.
- Forced-password, platform, tenant role, and subscription states have dedicated
  frontend guards and screens.
- Current UI supports light/dark themes, English/Arabic, RTL, and mobile dashboard
  layout smoke coverage.

## Exact recommended implementation phases

### Phase 77B: production identity and configuration gates

1. Disable public registration in production or require an invitation.
2. Implement supported platform-owner bootstrap and break-glass recovery.
3. Replace/strengthen session handling, shorten token lifetime, revoke sessions
   on password change/deactivation, and decide platform-admin MFA.
4. Add shared rate limiting and trusted-proxy client-IP handling.
5. Add fail-closed production configuration validation and tests.
6. Normalize API error envelopes and remove avoidable public metadata.

Exit: security regression suite passes and a new environment fails startup when
any production-required value is unsafe or missing.

### Phase 77C: deployability and recoverability

1. Select hosting, PostgreSQL, DNS, TLS, secret manager, and log/monitor vendors.
2. Add reproducible backend/frontend deployment artifacts and a staging topology.
3. Add migration preflight, release, rollback, and database compatibility checks.
4. Automate encrypted backups and complete a documented restore drill.
5. Add monitoring, alerts, structured logs, request IDs, dashboards, and runbooks.
6. Load-test critical accounting/report/export operations.

Exit: staging deploys from a tagged commit without manual file edits, backup
restore meets RPO/RTO, and rollback is rehearsed.

### Phase 77D: legal, data governance, and commercial operations

1. Approve Terms, Privacy Notice, DPA, subprocessor list, retention/deletion,
   breach response, and accounting/AI disclaimers with counsel.
2. Define supported jurisdictions and explicitly excluded accounting functions.
3. Define subscription billing, invoice, renewal, suspension, cancellation,
   refund, data export, and termination policies.
4. Define support hours, severity levels, escalation, SLA/SLO, and ownership.

Exit: customer contract and in-product/public notices are approved and support
can execute the full lifecycle without database edits.

### Phase 77E: production pilot certification

1. Provision an empty production database and apply migrations.
2. Bootstrap the platform owner, change the temporary password, and enable MFA.
3. Execute the manual QA, deployment, and handover checklists below in staging.
4. Onboard one internal/canary tenant, reconcile reports against known fixtures,
   exercise suspension/reactivation, export data, and restore a backup.
5. Record sign-off from engineering, operations, security/privacy, accounting,
   support, and the business owner.

Exit: all critical blockers and pre-pilot high items are closed; no open Severity
1/2 defects; rollback and incident contacts are current. Decision changes to GO.

### Phase 77F: post-launch hardening

Add deeper performance work, accessibility certification, dependency automation,
customer self-service export/deletion, expanded accounting modules, and service
status/release automation based on measured pilot needs.

## Manual QA checklist

### Identity and authorization

- [ ] Public registration is unavailable or invitation-gated in production.
- [ ] Invalid login responses do not reveal whether an email exists.
- [ ] Login rate limits work across two API workers and through the proxy.
- [ ] Platform admin lands on Platform Dashboard and cannot open tenant data.
- [ ] Company admin and normal user cannot open any `/platform/*` route/API.
- [ ] Tenant A user cannot discover or access Tenant B company, users, accounts,
      journals, reports, audit logs, conversations, exports, or subscription state.
- [ ] Temporary login reaches only identity/password-change endpoints.
- [ ] Current password is verified; weak, reused, and mismatched passwords fail.
- [ ] Password change/deactivation invalidates existing sessions on other devices.
- [ ] Final active platform owner cannot be deactivated; break-glass recovery works.

### Onboarding and subscription

- [ ] Platform owner onboards a unique client and receives the HTTPS login URL.
- [ ] Temporary password appears once and never appears in logs or audit data.
- [ ] Client admin belongs only to the new company; platform owner is not a member.
- [ ] Standard chart is default; blank creates none; Yemen starter is optional.
- [ ] No demo journals are created during real onboarding.
- [ ] Trial/active expiry, past due, suspend, cancel, extend, and reactivate behave
      correctly; non-members do not learn subscription state.

### Accounting and AI

- [ ] Create custom cash, bank, wallet, receivable, revenue, and expense accounts.
- [ ] Create balanced draft; reject unbalanced and invalid debit/credit lines.
- [ ] Review/post; reject closed-period posting and direct posted-entry edits.
- [ ] Reverse a posted entry and verify trial balance and ledgers.
- [ ] Reconcile Trial Balance, Profit and Loss, Balance Sheet, General Ledger, and
      Account Ledger against an accountant-approved fixture.
- [ ] Verify CSV/PDF exports and Arabic text rendering.
- [ ] AI follow-up memory stays inside user/company/conversation and a context-free
      follow-up asks for clarification. AI never posts without confirmation.

### Frontend and resilience

- [ ] Validate desktop/mobile, English/Arabic, RTL/LTR, light/dark, and supported
      browsers over the production domain.
- [ ] Refresh every SPA route directly; history fallback returns the app.
- [ ] Simulate 401, 403, 409, 422, 429, 500, network loss, and expired subscription.
- [ ] Verify API calls never target localhost and contain no mixed HTTP content.
- [ ] Confirm logs, metrics, traces/errors, uptime alerts, and backup alerts fire.

## Deployment checklist

- [ ] Approved tagged commit and immutable build artifacts identified.
- [ ] Full backend/frontend CI green; dependency and secret scans green.
- [ ] Production variables reviewed against `production-env.example.md`.
- [ ] Separate least-privilege production database and credentials provisioned.
- [ ] Empty database confirmed; no demo users, companies, or journal data copied.
- [ ] Encrypted pre-deploy backup taken; restore target and operator confirmed.
- [ ] `alembic heads` returns one head; migration reviewed for locks/data impact.
- [ ] Run `alembic upgrade head` once as a controlled release step.
- [ ] Backend runs without reload; frontend is static; HTTPS and security headers pass.
- [ ] Exact CORS origins and API/public URLs resolve to the production domain.
- [ ] Health/readiness checks, worker restarts, log collection, monitoring, and alerts pass.
- [ ] Platform owner bootstrapped through the supported command and password changed.
- [ ] Smoke-test identity, platform, onboarding, tenant accounting, reports, and exports.
- [ ] Record deployed commit, migration revision, operator, timestamp, and sign-off.
- [ ] Keep previous application artifact and documented database rollback/recovery plan.

## Customer handover checklist

- [ ] Contract, privacy/DPA, subprocessor, supported-scope, accounting/AI disclaimer,
      support, billing, cancellation, and retention terms accepted.
- [ ] Customer company name, legal identity, currency, jurisdiction, fiscal year,
      chart choice, roles, subscription term, and authorized contacts confirmed.
- [ ] Client admin created through platform onboarding; platform owner is not a member.
- [ ] HTTPS URL, admin email, and one-time temporary password sent through approved
      channels; do not place both factors in the same insecure channel where avoidable.
- [ ] Client changes password immediately and MFA is enrolled when available.
- [ ] Client verifies company scope, opening balances/chart, fiscal periods, users,
      reports, export, and subscription details.
- [ ] Demo identities (`admin@example.com`, documented demo password), demo companies,
      test domains, cleanup artifacts, and local databases are absent from production.
- [ ] Customer receives user guide, supported-browser list, support route, severity
      expectations, backup/data-export policy, and incident contact.
- [ ] Handover acceptance and accountable signatories are recorded without passwords.

## Final production gate

Do not change this audit to GO because the code builds or because a public demo
works. GO requires closure evidence for C1-C6, all pre-pilot high items, a clean
production database, a successful staging restore and rollback exercise, manual
QA evidence, and business/legal/accounting sign-off.
