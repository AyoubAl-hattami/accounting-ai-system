# Clean Architecture Roadmap

## Why this migration is needed

The project has grown into a substantial accounting platform with authentication,
company-scoped RBAC, accounts, fiscal calendars, journals, reports, audit logs,
exports, and AI assistants. Its feature naming is clear, but several files now
combine too many responsibilities:

- `journal_routes.py` contains HTTP handling, authorization, accounting
  validation, lifecycle orchestration, transaction completion, and auditing.
- `journal_service.py` combines SQLAlchemy access with journal lifecycle
  mutations and accounting calculations.
- `report_service.py` combines optimized SQL, accounting classification,
  calculations, and response construction.
- `gemini_assistant_service.py` combines intent handling, permissions, grounding,
  report access, provider calls, fallback replies, localization, and dispatch.
- Backend transaction ownership is divided among routes, services, and audit
  helpers.
- Frontend pages and assistant components combine API state, permissions,
  workflow logic, presentation, responsive variants, and extensive Tailwind
  styling.
- Theme colors are partly centralized but still repeated directly throughout
  JSX, making visual changes broad and risky.

The target is not a large rewrite. It is a sequence of compatibility-preserving
changes that move policy toward the center and frameworks toward the edges.

## Target architecture at a glance

### Backend

- **Domain:** accounting invariants, journal transition policies, fiscal rules,
  identity value objects, and framework-independent errors.
- **Application:** commands, queries, use cases, ports, authorization
  orchestration, transaction ownership, and audit-event coordination.
- **Infrastructure:** SQLAlchemy models and repositories, PostgreSQL, AI SDKs,
  security implementations, audit persistence, and CSV/PDF exporters.
- **Interfaces:** FastAPI routes, dependencies, Pydantic API schemas, error
  translation, and serialization.
- **Core:** minimal configuration and technical primitives that truly apply
  across bounded contexts.

### Frontend

- **App:** providers, routes, application shell, and initialization.
- **Shared:** UI primitives, semantic theme, transport client, generic hooks,
  utilities, and i18n infrastructure.
- **Entities:** reusable account, journal, company, user, fiscal-period, and
  audit-event models and presentation.
- **Features:** user actions such as creating or posting a journal entry,
  managing company access, exporting a report, or confirming an assistant action.
- **Widgets:** composed application regions such as navigation, company selector,
  report toolbar, dashboard summary, and assistant drawer.
- **Pages:** route-level composition with little deep business logic.

### AI

Application ports describe journal suggestion, intent classification, and
accounting answer capabilities. Rules, Gemini, and OpenAI are infrastructure
adapters. Permission checks, company scope, accounting grounding, and explicit
mutation confirmation remain application responsibilities.

### Database and repositories

Repositories isolate persistence operations behind application-owned ports.
Optimized report readers remain SQL-oriented adapters. A unit of work owns the
transaction; repositories may flush but do not commit.

### Reports

Reports are separated into authorized application queries, persistence-optimized
readers, pure calculation/classification policies where practical, and API,
CSV, or PDF presenters.

### Theme

Semantic CSS variables and Tailwind tokens define surfaces, content, borders,
accents, and financial states. Shared UI primitives consume those tokens.
Components use layout utilities freely but avoid embedding theme palette choices.

## Compatibility policy

Every phase must preserve API contracts, database schema, Alembic history,
accounting calculations, journal lifecycle, RBAC and company isolation, audit
atomicity, AI confirmation safety, frontend route URLs, and Arabic/RTL behavior.
Schema or product changes require separate decisions and must not be hidden
inside architecture work.

## Migration phases

### Phase 0: Baseline and freeze behavior

**Goal:** Establish an observable contract before structural changes.

Document endpoint contracts, transaction callers, journal invariants, RBAC
matrix, report fixtures, assistant fallbacks, and frontend routes. Capture the
normal verification commands and representative accounting results.

**Risk:** Low.

**Verification:** Full existing backend tests, frontend build/lint, API contract
checks, migration-head checks, report reconciliation, and focused RTL/manual UI
checks when execution is authorized.

**Rollback:** Documentation can be reverted independently.

**Commit:** Separate baseline/documentation commit.

### Phase 1: Documentation and boundaries

**Goal:** Establish vocabulary, ownership, allowed dependencies, and target
packages without moving production logic.

Add architecture decision records and optional empty package scaffolding only
when required by the first pilot. Define transaction and compatibility rules.

**Risk:** Low.

**Verification:** Existing imports and runtime behavior remain unchanged.

**Rollback:** Remove documentation or unused scaffolding.

**Commit:** Separate.

### Phase 2: Backend ports and repositories pilot

**Goal:** Introduce repository and unit-of-work protocols alongside current
services.

Start with narrow account or fiscal interfaces. Concrete SQLAlchemy adapters may
delegate to existing query code. Do not change table mappings or Alembic imports.

**Risk:** Medium.

**Verification:** Repository contract tests, unchanged endpoint tests, audit
atomicity, and rollback behavior.

**Rollback:** Keep current services callable until the adapter proves parity.

**Commit:** Separate by port or bounded context.

### Phase 3: Accounts/fiscal pilot

**Goal:** Migrate one lower-risk backend feature end to end.

Accounts or fiscal settings are preferable to journal posting. Introduce
commands/queries, a use case, repository adapter, API error translation, and a
unit-of-work boundary while preserving the endpoint contract.

**Risk:** Medium.

**Verification:** CRUD/query behavior, company scoping, RBAC, validation, audit
records, fiscal boundaries, response serialization, and transaction failure.

**Rollback:** Route the endpoint back to the current service.

**Commit:** One focused feature commit, or separate query and mutation commits.

### Phase 4: Journal use cases

**Goal:** Extract journal invariants and migrate lifecycle operations safely.

Move balanced-entry validation and permissible transitions into pure domain
policies. Add application use cases for create, update, review, post, reverse,
void, and opening balance. Move one operation at a time.

**Risk:** Very high.

**Verification:** Journal balance, numbering, account ownership, fiscal period,
status transitions, immutability, reversal relationships, concurrency,
transaction atomicity, and audit tests. Reconcile ledger results before and
after.

**Rollback:** Preserve the old implementation behind the same endpoint until
each operation reaches parity.

**Commit:** Separate per lifecycle operation or tightly related pair.

### Phase 5: Reports

**Goal:** Separate report reads, accounting semantics, and presentation.

Introduce report-reader ports backed by optimized SQL. Extract calculations and
classification rules where they can be pure. Keep CSV and PDF rendering as
outbound adapters.

**Risk:** High.

**Verification:** Exact totals for trial balance, profit and loss, balance sheet,
account ledger, and general ledger; date and fiscal boundaries; posted-entry
filters; company isolation; CSV/PDF parity.

**Rollback:** Retain existing report functions as compatibility adapters.

**Commit:** Shared report foundation separately, then one report type per commit.

### Phase 6: AI assistant/provider decomposition

**Goal:** Make the accounting assistant provider-neutral and break the large
assistant service into focused use cases.

Move provider contracts to application ports. Keep prompt construction, SDK
calls, provider response parsing, and provider configuration in infrastructure.
Keep grounding, permissions, company scope, and confirmation orchestration in
application.

**Risk:** High.

**Verification:** Rules/Gemini/OpenAI fallback, invalid-output handling, prompt
injection protection, company isolation, grounding, bilingual responses,
conversation context, and explicit action confirmation.

**Rollback:** Keep the current dispatcher as a compatibility facade while new
components are adopted.

**Commit:** Provider boundary, orchestration split, and thin-route integration
as separate commits.

### Phase 7: Frontend shared UI/theme system

**Goal:** Centralize semantic visual decisions and reusable UI patterns.

Introduce semantic colors, chart tokens, typography, elevation, and shared page,
table, modal, form, status, money, and feedback primitives. New primitives
remain opt-in.

**Risk:** Medium.

**Verification:** Light/dark contrast, responsive layouts, focus states, RTL,
Arabic text, financial number readability, and visual regression checks.

**Rollback:** Existing components remain available until consumers migrate.

**Commit:** Theme tokens separately from shared component additions.

### Phase 8: Frontend pilot page

**Goal:** Prove app/shared/entity/feature/widget/page boundaries on one page.

Accounts or Settings is preferable to journals or reports. Move API interaction
to an entity or feature adapter, user actions to features, and route composition
to a page.

**Risk:** Medium.

**Verification:** Route URL, permissions, API calls, loading/error/empty states,
mutations, responsive behavior, dark mode, and RTL.

**Rollback:** Keep the old page until manual and automated parity is confirmed.

**Commit:** Separate page migration.

### Phase 9: Journal/report UI migration

**Goal:** Apply proven shared components to the most complex workflows.

Split journal actions into features and report shells into reusable widgets.
Migrate one modal, action, or report at a time.

**Risk:** High.

**Verification:** Every workflow state, monetary formatting, filters, exports,
desktop/mobile tables, permissions, assistant integration, and Arabic/RTL.

**Rollback:** Maintain per-route or per-component compatibility during migration.

**Commit:** Separate by journal workflow or report.

### Phase 10: Cleanup and enforcement

**Goal:** Remove proven-obsolete compatibility code and automate dependency
rules.

Add backend import-boundary checks and frontend layer import rules. Remove old
services or components only after all callers have migrated.

**Risk:** Medium to high.

**Verification:** Full project baseline, architecture checks, unused-import
checks, database metadata checks, and manual critical-workflow QA.

**Rollback:** Use small deletion commits that can be reverted independently.

**Commit:** Multiple focused cleanup commits.

## Recommended pilot

Begin with an account repository port and one account query or mutation use case
after the baseline is recorded. Do not start with journal posting, reports, the
Gemini assistant, or a global theme rewrite.
