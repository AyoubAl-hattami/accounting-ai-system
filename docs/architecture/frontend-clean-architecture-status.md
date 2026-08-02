# Frontend Clean Architecture Status

**Status date:** 2026-08-02  
**Branch:** phase-56-to-60-frontend-clean-migration  
**Rollback point:** `stable-clean-architecture-2026-08-02`

---

## Layer structure

```
shared/       ← transport, theme, utility (no upward imports)
  api/        ← axios instance (shared/api/index.ts re-exports api/client)
  theme/      ← CSS tokens, Tailwind config
entities/     ← domain types + thin presentational atoms (no feature imports)
  account/    ← Account type, AccountSeedResult type, AccountTypeBadge component
  audit-event/
  company/
  fiscal-period/
  journal/
  user/
features/     ← live legacy feature slices (state hooks + full UI components)
features-clean/ ← clean architecture pilot stubs (hooks + API only, no UI)
pages-clean/  ← migration scaffold placeholders (README only)
app/          ← application shell (README only)
routes/       ← (does not exist as a populated layer yet)
components/   ← shared UI kit (layout, feedback, charts)
auth/         ← auth context and guards
i18n/         ← internationalisation
```

---

## Phase 56 — completed (2026-08-02)

### What was migrated

**AccountTypeBadge promoted to entity layer.**

`AccountTypeBadge` was a pure presentational component (React + Tailwind, no
state, no API calls) living in `features/accounts/`.  Five report pages and
`CreateJournalEntryModal` imported it across feature boundaries, creating seven
forbidden cross-feature import violations.

Changes made:
- Created `entities/account/AccountTypeBadge.tsx` (named export `AccountTypeBadge`).
- Updated `entities/account/index.ts` to export the component.
- Updated six files to import `{ AccountTypeBadge }` from `../../../entities/account`
  (report pages) or `../../entities/account` (journals modal).
- Reduced the architecture guard allowlist from 7 entries to 1.
- All four architecture guard tests pass; tsc and build remain green.

Files updated:
```
frontend/src/entities/account/AccountTypeBadge.tsx   (new)
frontend/src/entities/account/index.ts               (updated)
frontend/src/features/reports/account-ledger/AccountLedgerPage.tsx
frontend/src/features/reports/balance-sheet/BalanceSheetPage.tsx
frontend/src/features/reports/general-ledger/GeneralLedgerPage.tsx
frontend/src/features/reports/profit-and-loss/ProfitAndLossPage.tsx
frontend/src/features/reports/trial-balance/TrialBalancePage.tsx
frontend/src/features/journals/CreateJournalEntryModal.tsx
frontend/tests/architecture_guard.test.mjs           (allowlist 7 → 1)
```

### What was intentionally kept legacy

`features/accounts/AccountTypeBadge.tsx` is **retained** (not deleted).
`AccountsPage.tsx` still imports it via the local `./AccountTypeBadge` path,
which is an intra-feature import (same slice) and does not violate any guard.
Deleting the file would require updating `AccountsPage.tsx` as well; that is
safe but deferred to keep this phase minimal and reversible.

`features/accounts/useAccounts` is **retained** as-is.  One remaining allowlist
entry covers `CreateJournalEntryModal.tsx → features/accounts/useAccounts`.
Moving `useAccounts` to the entity layer is architecturally incorrect (hooks own
local React state; entities should be stateless types).  The correct fix is to
lift account selection out of the modal or create a dedicated hook — this
requires a UI refactor deferred to Phase 57+.

`features-clean/` scaffold stubs are **not wired into live routes**.  The
architecture guard `'live app must not import from features-clean or pages-clean'`
remains active.  `features-clean/` provides clean API/hook patterns as reference
for future slice migrations but has no UI components and cannot replace the live
`features/` pages without a full component build-out.

---

## Phase 57 — blocked (2026-08-02)

**Blocker: no test framework in package.json.**

Vitest, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` are
absent from `frontend/package.json`.  Installing them requires:

```sh
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom \
  @testing-library/user-event jsdom
```

This must be done in an environment where `npm install` can run and the updated
`package-lock.json` can be committed.  The CI workflow (`frontend-validation.yml`)
must also add a `npm run test -- --run` step.

Until Phase 57 is unblocked, the existing `node --test` architecture guard
remains the only automated frontend test.

**Safe to add when unblocked:**
- Dashboard render smoke with `vi.mock` on axios
- Accounts list render with mocked paginated response
- AccountTypeBadge renders correct colour class for each account type
- Report page renders empty state without crashing

---

## Phase 58 — documented (2026-08-02)

Manual smoke checklist created at `docs/frontend/ui-smoke-checklist.md`.
Covers: Login, Dashboard, Accounts, Journal Entries, Reports (5 views),
Audit Logs, Company Users, Settings, AI Assistant, cross-cutting concerns.

---

## Architecture guard status

```
frontend/tests/architecture_guard.test.mjs — 4/4 tests PASS

LEGACY_FEATURE_CROSS_IMPORT_ALLOWLIST (1 entry remaining):
  features/journals/CreateJournalEntryModal.tsx → features/accounts/useAccounts

Goal: empty this list in Phase 57+ by lifting account selection out of the modal.
```

---

## Validation commands

```powershell
$env:Path = "C:\nodejs;$env:Path"
cd C:\ayoub\accounting-ai-system

# Architecture guard
node --test frontend/tests/architecture_guard.test.mjs

# TypeScript
cd frontend; npx tsc -b --noEmit; cd ..

# Lint
npm run lint --prefix frontend

# Production build
npm run build --prefix frontend -- --outDir dist-clean-check
Remove-Item -Recurse -Force frontend/dist-clean-check
```

---

## Current CI status

After PR #31 merged to main:
- `Backend validation` (static + PostgreSQL): green
- `Frontend validation` (tsc + eslint + build + architecture guard): green

---

## Recommended next steps (Phase 57+)

1. **Add Vitest** — install dev dependencies, add `vitest.config.ts`, wire into
   `frontend-validation.yml`.
2. **Write AccountTypeBadge unit test** — straightforward; no mocking needed.
3. **Lift account selection from CreateJournalEntryModal** — eliminate the last
   allowlist entry by passing `accounts` as a prop from `JournalEntriesPage` or
   creating an intra-feature `useAccounts` copy in `features/journals/`.
4. **Delete `features/accounts/AccountTypeBadge.tsx`** after updating
   `AccountsPage.tsx` to import from `entities/account`.
5. **Migrate full feature slices** — replace `features/` pages with `features-clean/`
   equivalents one slice at a time, starting with Dashboard (simplest API contract).
