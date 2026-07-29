# Theme Architecture

## Current problem

The frontend has both centralized theme mechanisms and extensive direct color
selection. `globals.css` defines CSS variables and shared component classes, but
AppShell, journal pages, report pages, dashboard components, modals, company
management, and the Gemini assistant still contain many `text-violet-*`,
`bg-violet-*`, `text-gray-*`, `text-slate-*`, `bg-white`, `border-violet-*`,
`brand-*`, and paired `dark:*` classes.

This makes a palette change affect many unrelated files. It also encourages
purple to be used for ordinary secondary text rather than reserved as a brand
accent.

## Direction

The theme should use semantic decisions:

```text
foundation palette -> semantic tokens -> component variants -> feature UI
```

Feature components should not need to know the exact violet, slate, gray, navy,
or charcoal shade used by the current theme.

## Semantic CSS variables

Recommended variable families:

```css
--color-page
--color-surface
--color-surface-subtle
--color-surface-elevated

--color-content
--color-content-secondary
--color-content-muted
--color-content-inverse

--color-border
--color-border-subtle
--color-focus

--color-accent
--color-accent-hover
--color-accent-subtle
--color-on-accent

--color-success
--color-warning
--color-danger
--color-info

--color-debit
--color-credit
--color-balance
```

Variables should also cover elevation, radius, and chart series where CSS is the
consumer. Light and dark modes redefine semantic variables rather than forcing
each component to select a separate palette.

## Semantic Tailwind tokens

Tailwind should expose semantic utilities:

```text
bg-page
bg-surface
bg-surface-subtle
text-content
text-content-secondary
text-content-muted
border-default
border-subtle
bg-accent
text-on-accent
text-success
text-danger
text-debit
text-credit
```

Direct Tailwind utilities remain appropriate for spacing, flex/grid, sizing,
responsive behavior, typography scale, and deliberate one-off data
visualizations. Theme-defining palette utilities should be exceptional.

## Calm color direction

### Light mode

- White primary surfaces.
- Soft neutral gray page background with, at most, a very subtle lavender tint.
- Slate or neutral-dark body and table text.
- Neutral secondary and muted text.
- Purple limited to primary actions, active navigation, focus, logo, and links.
- Stable success, warning, danger, debit, and credit semantics.

### Dark mode

- Neutral navy or charcoal page background.
- Slightly elevated neutral surfaces.
- Readable near-white content and restrained neutral secondary text.
- Purple as a subtle interactive accent, without glow or neon treatment.
- Borders expressed through quiet contrast rather than bright outlines.

## Shared UI primitives

The following components should own their semantic styling:

- Buttons and icon buttons.
- Inputs, selects, textareas, and field messages.
- Modal and drawer surfaces.
- Page headers and toolbars.
- Table shell, headers, rows, totals, and money cells.
- Cards and summary statistics.
- Status badges and alerts.
- Loading, error, empty, and access-denied states.
- Assistant messages, composer, and suggested accounting-action cards.

Variants should express intent such as `primary`, `secondary`, `danger`,
`success`, `debit`, or `credit`, not raw color names.

## Chart theme

Charts require a centralized TypeScript theme because many chart libraries
consume literal color values rather than CSS classes.

`shared/theme/charts.ts` should define:

- Ordered categorical series.
- Revenue/expense and asset/liability/equity colors.
- Debit/credit colors.
- Grid, axis, tooltip, and label colors for both modes.
- Accessible contrast and distinguishability.

Dashboard and report components should import chart semantics rather than define
hex values locally.

## Reports and accounting presentation

Report tables should use neutral text for codes, names, dates, and totals.
Semantic colors should communicate meaning:

- Debit and credit where color improves scanning.
- Success, warning, and imbalance states.
- Posted, draft, reviewed, reversed, and void status.

Color must never be the only carrier of accounting meaning. Labels, signs,
columns, icons, or status text remain necessary.

## Assistant styling

The assistant should consume the same surface, content, border, accent, and
status tokens as the rest of the application. It may have a restrained
assistant-specific surface token, but it must not establish a second neon or
provider-branded theme.

Suggested action cards use accounting workflow semantics for debit, credit,
confirmation, and cancellation. Provider identity must not drive the color
system.

## Migration sequence

1. Inventory current palette utilities and literal chart colors.
2. Define semantic variables without changing component appearance.
3. Map semantic Tailwind tokens.
4. Migrate shared inputs, buttons, modals, tables, and page headers.
5. Migrate AppShell and company selector.
6. Migrate one lower-risk page.
7. Migrate report and journal UI incrementally.
8. Migrate assistant surfaces and action cards.
9. Centralize charts.
10. Remove obsolete direct palette classes and enforce new usage.

Do not combine token introduction with a broad visual redesign. First reproduce
the current appearance through semantic tokens; a calmer palette can then be
changed centrally and reviewed independently.

## Compatibility requirements

Theme migration must preserve responsive behavior, focus visibility, frontend
route URLs, authorization-driven control visibility, financial meaning,
translations, and Arabic/RTL layout. It must not alter API behavior or
accounting workflows.
