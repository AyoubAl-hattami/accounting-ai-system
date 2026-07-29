# Frontend Target Architecture

## Target structure

```text
frontend/src/
  app/
    providers/
    routes/
    layout/
    styles/

  shared/
    ui/
    theme/
    api/
    lib/
    hooks/
    i18n/
    types/

  entities/
    account/
    journal/
    company/
    user/
    fiscal-period/
    audit-event/

  features/
    journal-entry-create/
    journal-entry-review/
    journal-entry-post/
    journal-entry-reverse/
    company-user-management/
    report-export/
    ai-journal-suggestion/
    accounting-assistant/

  widgets/
    navigation/
    company-selector/
    dashboard-summary/
    report-toolbar/
    assistant-drawer/

  pages/
    dashboard/
    accounts/
    journal-entries/
    reports/
    audit/
    settings/
```

The current feature directories provide a useful starting point. The target is
clearer responsibility inside those areas, not a one-time move of every file.

## App

`app` owns application-wide composition:

- React providers and initialization.
- Route definitions and protected-route wiring.
- Main shell and layout composition.
- Global error boundaries.
- Global style entry points.

It should not contain account, journal, report, or assistant workflow logic.
Existing frontend route URLs must remain unchanged.

## Shared UI

`shared/ui` contains business-neutral components such as:

- Button and icon button.
- Input, select, textarea, and field wrapper.
- Modal, drawer, popover, and confirmation dialog.
- Page header and toolbar.
- Data table shell and responsive list shell.
- Loading, error, empty, and access-denied states.
- Status badge primitives.
- Money and numeric display primitives.

Shared UI receives state and callbacks. It must not fetch journal entries,
inspect company roles, or import feature hooks.

## Shared theme

`shared/theme` owns:

- Semantic CSS variables.
- Tailwind semantic token mapping.
- Typography, radius, spacing, elevation, and focus decisions.
- Light and dark modes.
- Chart series and report visualization colors.
- Financial status, debit, credit, success, warning, and danger semantics.

Components should use names such as `text-content`, `text-muted`, `bg-surface`,
`border-subtle`, and `text-debit` instead of independently selecting raw palette
values.

## Shared API

`shared/api` owns transport mechanics:

- Axios client creation.
- Authentication headers/interceptors.
- Error normalization.
- Cancellation and generic request support.

It should not become a flat collection of every accounting endpoint. Entity and
feature modules own their typed endpoint adapters and query/mutation behavior.

## Shared lib, hooks, i18n, and types

- `shared/lib` contains framework-neutral formatting and small utilities.
- `shared/hooks` contains generic hooks with no accounting feature dependency.
- `shared/i18n` contains translation infrastructure and locale direction.
- `shared/types` contains truly cross-cutting technical types, not all API DTOs.

Accounting money formatting, date interpretation, and language direction should
have one trusted implementation.

## Entities

Entities expose reusable frontend representations of business concepts:

- Types and mapping for an account, journal, company, user, fiscal period, or
  audit event.
- Typed entity API functions and query keys.
- Entity-specific formatters and small display components.
- Stable public exports.

Entities do not own route layout or multi-step user workflows.

## Features

A feature represents a user action with its state, permission rules, API
mutation/query composition, validation, and UI:

- Create, review, post, reverse, or void a journal entry.
- Invite or manage a company user.
- Export a report.
- Ask the accounting assistant.
- Confirm an AI-proposed journal draft.

Features may depend on entities and shared modules. They must not import pages.

## Widgets

Widgets compose several features or entities into a reusable application region:

- Navigation and company selector.
- Dashboard summary.
- Report filter/export toolbar.
- Journal action area.
- Global assistant drawer.

A widget may know layout and feature composition but should not own backend
accounting policy.

## Pages

Pages map route intent to composed UI. They should:

- Select the required widgets and features.
- Pass route parameters.
- Define page-level layout and metadata.
- Handle only route-level loading or access boundaries.

Large page files should not retain:

- Raw Axios calls and response normalization.
- Multiple mutation implementations.
- Accounting lifecycle policy.
- Repeated permission matrices.
- Reusable tables, filter bars, status badges, or modal shells.
- Chart palette literals.
- Hundreds of direct light/dark color decisions.
- Desktop and mobile implementations with duplicated business logic.

## Reports UI structure

Reports should share:

```text
shared/ui/
  Money/
  DataTable/

widgets/report-toolbar/
features/report-export/
entities/account/

pages/reports/
  trial-balance/
  profit-and-loss/
  balance-sheet/
  account-ledger/
  general-ledger/
```

A shared report shell should own consistent title, company context, date filters,
loading/error/empty states, export actions, summary grid, and responsive layout.
Each report owns only its columns, calculations received from the API, and
report-specific visualization.

Frontend report code must not recreate authoritative accounting totals already
defined by the backend. Client-side calculations should be limited to display or
explicitly verified derived views.

## Assistant UI structure

The assistant should be provider-neutral:

```text
features/accounting-assistant/
  api/
  model/
  ui/
    MessageList.tsx
    Composer.tsx
    HistoryPanel.tsx
    SuggestedActionCard.tsx

widgets/assistant-drawer/
```

Conversation state, API mapping, message rendering, composer behavior, history,
and suggested accounting actions should be separable. The UI consumes
capabilities such as reply, grounding, confidence, and suggested action; it
should not structurally depend on Gemini-specific implementation details.

Explicit confirmation for mutations must remain visible and cannot be bypassed
by component refactoring.

## Migration rules

- Create semantic tokens and primitives before migrating feature pages.
- Pilot a lower-risk page such as Accounts or Settings.
- Migrate one report or journal workflow at a time.
- Preserve URL paths, API contracts, authorization visibility, translations,
  keyboard behavior, responsive layouts, and Arabic/RTL.
- Do not combine global visual redesign with page architecture extraction.
