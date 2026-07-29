# Frontend Baseline

## Route map

Routes are defined in `frontend/src/routes/AppRoutes.tsx`.

Public routes:

- `/login`
- `/accept-invite`

Protected application routes:

- `/dashboard`
- `/accounts`
- `/journal-entries`
- `/reports/trial-balance`
- `/reports/profit-and-loss`
- `/reports/balance-sheet`
- `/reports/account-ledger`
- `/reports/general-ledger`
- `/audit-logs`
- `/company-users`
- `/settings`

`/` and unknown paths currently redirect to `/dashboard`. Future page
reorganization must not change these URLs or protection behavior.

## Login

- Accepts the current email/password flow.
- Displays current validation and authentication failures.
- Stores/uses the existing bearer token mechanism.
- Redirects authenticated users according to current application behavior.
- Inactive or invalid users cannot enter protected areas.
- English and Arabic input/layout remain functional.

## Application shell

`frontend/src/components/layout/AppShell.tsx` currently provides:

- Primary navigation.
- Reports navigation.
- Company context/selector integration.
- Theme control.
- Language control.
- User identity and sign-out.
- Responsive sidebar behavior.
- Permission-filtered navigation.

Refactoring must preserve selected route indication, collapse/mobile behavior,
company switching, control visibility, and RTL layout.

## Dashboard

- Loads company-scoped summary information.
- Displays current accounting metrics and chart data.
- Handles loading, error, empty, and selected-company states.
- Uses the current date/number/currency formatting.
- Must not calculate authoritative report totals differently from the backend.

## Accounts

- Lists current company accounts with pagination/search/filter behavior.
- Supports authorized account creation/update and default-account seeding.
- Preserves account types, active state, validation, error display, and
  permission-dependent controls.

## Journal entries

- Lists company journal entries with current filtering, search, pagination,
  expansion/details, status display, and action visibility.
- Supports create, edit draft, review, post, reverse, and void workflows for
  authorized roles.
- Displays debit/credit amounts and lifecycle status consistently.
- Does not expose cross-company creator or entry information.

## Create journal modal

- Captures entry date, description/reference, and journal lines.
- Resolves/selects company accounts.
- Preserves debit/credit validation and balancing feedback.
- Displays fiscal/account/API errors without changing payload semantics.
- Supports keyboard, focus, responsive, dark, and RTL behavior.

## Journal assistant

- Provides the current journal-oriented suggestion flow.
- Suggestions remain advisory and populate/recommend data without bypassing
  journal validation.
- Provider failure retains the existing fallback/warning experience.
- User confirmation remains required before applicable mutations.

## Global AI assistant

- Opens from the global application experience without replacing accounting
  navigation.
- Supports conversation messages and history where currently available.
- Supports English and Arabic.
- Presents grounded responses and suggested accounting-action cards.
- Confirm/cancel controls remain explicit.
- Unauthorized actions remain unavailable even if model text requests them.

## Reports

All reports preserve company/date filters, loading/error/empty states, currency
formatting, responsive presentation, and CSV/PDF export behavior.

### Trial Balance

- Displays account debit/credit totals and balances.
- Clearly indicates the current balanced state/result.

### Profit & Loss

- Displays current revenue, expense, and net-result structure.

### Balance Sheet

- Displays current asset, liability, and equity structure and totals.

### Account Ledger

- Requires/selects an account and displays current opening balance, movements,
  and closing/totals behavior.

### General Ledger

- Displays current account groupings and journal movements.

Frontend changes must not recompute authoritative totals differently from report
API responses.

## Audit logs

- Shows authorized, company-scoped audit events.
- Preserves filters, pagination, timestamps, action/entity information, and
  loading/error states.
- Never displays protected tokens or secrets.

## Company users

- Lists company memberships and invitations.
- Preserves role and active/access distinctions.
- Allows company-scoped remove/restore behavior only where authorized.
- Shows global deactivate/reactivate controls only to platform superusers.
- Preserves last-admin, self-deactivation, final-superuser, cross-company, and
  invitation safeguards through backend error handling and UI visibility.

## Settings

- Preserves current user/company/fiscal settings workflows and access rules.
- Theme and language settings continue to apply across routes.
- Settings changes retain current API payloads and feedback.

## Language and Arabic/RTL

- Language switching retains current translation keys and selected language.
- Arabic sets natural RTL direction across shell, forms, tables, modals, report
  controls, and assistant UI.
- Navigation actions, header controls, close buttons, message bubbles, numeric
  values, and mixed Latin/accounting codes must not overlap or reverse
  incorrectly.
- English returns to LTR without stale layout state.

## Theme behavior

- The current light and dark mode toggle remains functional and persistent
  according to current implementation.
- All routes remain readable in both modes.
- Semantic accounting colors retain meaning.
- Theme refactoring must preserve focus visibility, contrast, responsive
  behavior, and chart readability.
- Existing direct Tailwind colors are a migration concern, not permission for a
  broad redesign during architecture work.

## Manual browser checklist

Using the commands in `verification-commands.md`:

1. Verify unauthenticated redirect/protection.
2. Log in and log out.
3. Select/switch company and confirm data isolation.
4. Visit every route in both English and Arabic.
5. Toggle light/dark mode on every high-density page.
6. Create or edit an account only in an approved test environment.
7. Open the journal creation modal; validate line entry and balance feedback.
8. Exercise authorized journal lifecycle actions on disposable data.
9. Verify every report, filter, and export action.
10. Open audit logs and verify scope/filter behavior.
11. Check company-user and invitation controls for admin, viewer, and
    superuser contexts.
12. Open journal and global assistants; verify fallback, grounding, history,
    suggested action, cancel, and explicit confirmation.
13. Check desktop, narrow desktop, and mobile widths.
14. Check keyboard focus, modal/drawer close behavior, scrolling, and no control
    overlap in RTL.

Record observed differences before accepting a refactor.
