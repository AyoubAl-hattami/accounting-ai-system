# Frontend Clean Architecture Status

**Status date:** 2026-08-02  
**Branch:** phase-61-frontend-real-component-migration  
**Rollback points:**
- `stable-clean-architecture-2026-08-02`
- `stable-frontend-clean-docs-2026-08-02`

---

## Layer structure

```
shared/       ← transport, theme, utility (no upward imports)
  api/        ← axios instance (shared/api/index.ts re-exports api/client)
  theme/      ← CSS tokens, Tailwind config
entities/     ← domain types + thin presentational atoms + reusable domain hooks
  account/    ← Account type, AccountSeedResult type, AccountTypeBadge, useAccounts
  audit-event/
  company/
  fiscal-period/
  journal/
  user/
features/     ← live feature slices (state hooks + full UI components)
features-clean/ ← clean architecture pilot stubs (hooks + API only, no UI) — staging only, not imported by live app
app/          ← application shell (README only)
components/   ← shared UI kit (layout, feedback, charts)
auth/         ← auth context and guards
i18n/         ← internationalisation
```

---

## Phase 61 — completed (2026-08-02)

### 61-A: Vitest + React Testing Library

Installed `vitest@4.x`, `@testing-library/react`, `@testing-library/jest-dom`,
`@testing-library/user-event`, `happy-dom` as dev dependencies.

Added:
- `frontend/vitest.config.ts` — uses happy-dom environment, includes only `src/**/*.test.{ts,tsx}`
- `frontend/src/test/setup.ts` — imports `@testing-library/jest-dom`
- `frontend/package.json` — added `"test": "vitest"` and `"test:run": "vitest --run"` scripts
- `.github/workflows/frontend-validation.yml` — added `npm run test:run` step after architecture guard

Note: `jsdom` was initially installed but swapped for `happy-dom` due to ESM incompatibility with `@csstools/css-calc` in the jsdom dependency tree.

### 61-B through 61-D: Accounts, Dashboard, Reports

After audit, no cross-feature imports were found in Dashboard, Reports, or Company Users features. These features were already architecturally compliant. No changes needed.

`AccountsPage.tsx` imported `AccountTypeBadge` from the local `./AccountTypeBadge` path (intra-feature). This was cleaned up as part of 61-E below.

### 61-E: Journal Create Modal migration + final allowlist removal

**Root cause:** `CreateJournalEntryModal.tsx` imported `useAccounts` from
`features/accounts/useAccounts`, a cross-feature import covered by the legacy
allowlist.

**Fix:** Promoted `useAccounts` to `entities/account/useAccounts.ts`.

The hook only calls `apiClient` (from `src/api/client`) and uses types from
`src/api/types` — no feature dependencies — making the entity layer the correct
home. `seedDefaults` is also a domain operation on the account resource.

Files changed:
```
frontend/src/entities/account/useAccounts.ts          (new — promoted from features)
frontend/src/entities/account/index.ts                (export useAccounts added)
frontend/src/features/journals/CreateJournalEntryModal.tsx  (import path updated)
frontend/src/features/accounts/AccountsPage.tsx       (import AccountTypeBadge + useAccounts from entities)
frontend/src/features/accounts/useAccounts.ts         (deleted — now in entities)
frontend/src/features/accounts/AccountTypeBadge.tsx   (deleted — canonical in entities since Phase 56)
frontend/tests/architecture_guard.test.mjs            (allowlist cleared to empty Set)
```

### 61-F: Company Users

After audit, `features/company-users/` has no cross-feature imports. No changes
needed. Feature is architecturally compliant as-is.

### 61-G: Architecture guard strict cleanup

`LEGACY_FEATURE_CROSS_IMPORT_ALLOWLIST` is now an **empty Set**. All four guard
tests pass. Any future cross-feature import will fail CI immediately.

Added comment in guard file documenting that Phase 61-E cleared the last entry.

### 61-H: File deletion

Deleted (proven unused by import search before deletion):
- `frontend/src/features/accounts/useAccounts.ts` — replaced by `entities/account/useAccounts.ts`
- `frontend/src/features/accounts/AccountTypeBadge.tsx` — replaced by `entities/account/AccountTypeBadge.tsx` (Phase 56)

`frontend/src/features-clean/` still exists as a staging scaffold. It is **not**
imported by the live app (architecture guard enforces this). It contains clean
API/hook reference implementations but no UI components. Retention rationale:
the staging code may be used as reference for future feature migrations and does
not cost anything since it is tree-shaken from the production bundle.

---

## Smoke tests added (Phase 61-A)

Location: `frontend/src/test/smoke/`

| Test file | Coverage |
|-----------|----------|
| `AccountTypeBadge.test.tsx` | Renders each of the 5 account types; handles unknown type |
| `useAccounts.test.ts` | Fetch success; fetch error; no-op when companyId is null; seedDefaults |

Total: **2 test files, 11 tests**.

Full-page component tests (AccountsPage, DashboardPage, etc.) are not included
because they require complex provider setup (router, auth context, company
context). These are documented as a future improvement. The smoke tests cover the
entity-layer logic that is most critical to validate.

---

## Architecture guard status

```
frontend/tests/architecture_guard.test.mjs — 4/4 tests PASS

LEGACY_FEATURE_CROSS_IMPORT_ALLOWLIST: EMPTY (0 entries)

All cross-feature imports are now forbidden with no exceptions.
```

---

## Validation commands

```powershell
$env:Path = "C:\nodejs;$env:Path"
cd C:\ayoub\accounting-ai-system

# Architecture guard (node:test, unchanged)
node --test frontend/tests/architecture_guard.test.mjs

# TypeScript
cd frontend; npx tsc -b --noEmit; cd ..

# Lint
npm run lint --prefix frontend

# Production build
npm run build --prefix frontend -- --outDir dist-clean-check
Remove-Item -Recurse -Force frontend/dist-clean-check

# Vitest
npm run test:run --prefix frontend
```

---

## Phase 56 — completed (2026-08-02) — reference

AccountTypeBadge promoted to entity layer; allowlist reduced from 7 → 1 entry.

---

## Phase 57-60 — completed (2026-08-02) — reference

Architecture docs and smoke checklist created. Vitest blocked on npm install
access; unblocked in Phase 61-A.

---

## Recommended next steps (Phase 62+)

1. **Add page-level smoke tests** — wrap AccountsPage in a minimal test provider
   (MemoryRouter + mock auth + mock company context) to cover loading/error/empty
   states without a real backend.
2. **Migrate features-clean stubs** — the staging hooks in `features-clean/`
   (accounts, dashboard, audit) are clean and could replace or supplement the
   live feature hooks if UI components are built alongside them.
3. **Promote entity API helpers** — `entities/account/useAccounts.ts` calls
   apiClient directly; consider extracting `entities/account/api.ts` to separate
   transport from the hook (mirrors `features-clean/accounts/api.ts` pattern).
