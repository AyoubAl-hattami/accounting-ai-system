# Frontend UI Smoke Checklist

**Phase 58 deliverable** — manual smoke validation for all core screens.  
Run against a locally-started dev server (`npm run dev --prefix frontend`) connected to
a running backend (`APP_ENV=development`).

Rollback point: `stable-clean-architecture-2026-08-02`

---

## Auth

### Login
- [ ] Unauthenticated user visiting `/` is redirected to login page.
- [ ] Invalid credentials show an inline error message (not a blank page).
- [ ] Valid credentials redirect to the dashboard.
- [ ] Token is stored and subsequent page loads do not re-redirect to login.

### Logout
- [ ] Logout clears token and returns user to login page.

---

## Dashboard

- [ ] Dashboard loads after login; at least one KPI card or chart is visible.
- [ ] Loading state (skeleton or spinner) is shown before data arrives.
- [ ] Error state is shown if the backend returns 5xx (simulate by stopping backend).
- [ ] Switching company (if multi-tenant) re-fetches dashboard data for the new company.

---

## Accounts

- [ ] Accounts page lists all accounts with code, name, type badge, and balance.
- [ ] AccountTypeBadge renders correctly (colour-coded by type: asset/liability/equity/income/expense).
- [ ] Pagination controls are visible and work (skip/limit respected).
- [ ] "Seed defaults" button populates a blank chart of accounts.
- [ ] Creating a new account shows the new row without page reload.
- [ ] Editing an account (name/description) reflects changes immediately.
- [ ] Deactivating an account removes it from the active list.
- [ ] Error messages are shown for duplicate codes or invalid input.

---

## Journal Entries

- [ ] Journal entries page lists entries with entry no, date, description, status badge.
- [ ] Filtering by status (draft / posted) works.
- [ ] "New entry" modal opens with empty lines and date defaulting to today.
- [ ] Account selector in modal shows accounts list; AccountTypeBadge appears per account.
- [ ] Debit/credit totals update live; submit is disabled when unbalanced.
- [ ] Draft entry can be reviewed and posted; posted entry cannot be edited.
- [ ] Reversing a posted entry creates a new reversal entry.
- [ ] AI assistant panel opens if the AI provider is configured.

---

## Reports

### Trial Balance
- [ ] Trial Balance renders debit/credit totals per account.
- [ ] AccountTypeBadge shown next to each account line.
- [ ] Date filter changes the displayed period.
- [ ] Empty state shown when no posted entries exist.

### Balance Sheet
- [ ] Balance Sheet renders assets, liabilities, equity sections.
- [ ] AccountTypeBadge shown per line.
- [ ] Export to CSV/PDF triggers a file download.

### Profit & Loss
- [ ] P&L renders revenue and expense accounts.
- [ ] AccountTypeBadge shown per line.
- [ ] Drill-down (if present) expands sub-account lines.

### General Ledger
- [ ] General Ledger lists all transaction lines grouped by account.
- [ ] AccountTypeBadge shown per account header.
- [ ] Date range filter works.

### Account Ledger
- [ ] Account Ledger shows lines for the selected account.
- [ ] AccountTypeBadge shown for the selected account.
- [ ] Selecting a different account re-fetches.

---

## Audit Logs

- [ ] Audit page shows log entries with action, entity, actor, timestamp.
- [ ] Filters (action type, date range) narrow results.
- [ ] Pagination works.
- [ ] Detail panel (if present) shows old/new values without exposing raw tokens.
- [ ] 403 is returned to non-admin users (verify in network tab).

---

## Company Users

- [ ] Company users page lists members with role badge and status.
- [ ] Admin can invite a new user by email; invitation row appears in pending list.
- [ ] Invitation cancellation removes the row from pending.
- [ ] Removing a user's access changes their status to inactive.
- [ ] Restoring access re-activates the member.
- [ ] Non-admin users cannot see the management actions.
- [ ] Inactive member invitation attempt shows "restore access" error (409).

---

## Settings

- [ ] Settings page loads fiscal years and periods.
- [ ] Creating a fiscal year and period succeeds.
- [ ] Closing a fiscal period prevents new journal entries in that period.

---

## AI Assistant (if provider configured)

- [ ] Assistant panel opens and accepts text input.
- [ ] Sending a message returns a response (may be rules-based in test mode).
- [ ] Pending transaction preview appears for journal-creation suggestions.
- [ ] Confirming suggestion creates a draft journal entry.

---

## Cross-cutting concerns

- [ ] Switching companies in the selector scopes all data to the new company.
- [ ] 401 responses clear the auth token and redirect to login.
- [ ] 403 responses show a permission-denied message (not a blank page).
- [ ] Empty states (no data) are shown with a helpful message, not a crash.
- [ ] All monetary values are formatted consistently (2 decimal places, correct currency symbol).
- [ ] RTL layout works correctly if Arabic locale is selected (if i18n is wired).

---

## Automated coverage (Phase 64)

Vitest + React Testing Library are installed (`npm run test:run --prefix frontend`).
As of Phase 64 the automated suite covers the following, deliberately narrow, slice:

- `entities/account/useAccounts` — fetch success/error/empty-companyId states, seed-defaults call
  (`frontend/src/test/smoke/useAccounts.test.ts`)
- `entities/account/AccountTypeBadge` — renders per account type
  (`frontend/src/test/smoke/AccountTypeBadge.test.tsx`)
- `features/audit/auditActionLabels.getActionLabel` — i18n lookup + Title Case fallback
  (`frontend/src/test/smoke/auditActionLabels.test.ts`)
- `features/company-users/CompanyUserRoleBadge` — renders label per role
  (`frontend/src/test/smoke/CompanyUserRoleBadge.test.tsx`)

Everything else on this checklist (Dashboard/Reports/Journal Entries full pages, Settings,
AI Assistant, cross-cutting auth/tenant/i18n behaviour) remains **manual-only** coverage.
Full-page tests for Dashboard/Reports/Journals were evaluated and deferred because they
require router + auth-context + company-context providers plus API mocking at a scale that
risks brittle, low-value tests; the pure hooks/helpers/badges above were chosen instead as
higher-value, stable targets. Expanding page-level automated coverage remains future work —
see `docs/frontend/e2e-readiness-plan.md` for the recommended path (Playwright E2E) rather
than deeper unit-test mocking of full pages.

---

*Last updated: Phase 64, 2026-08-02*
