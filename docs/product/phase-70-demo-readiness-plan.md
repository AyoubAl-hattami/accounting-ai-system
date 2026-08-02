# Phase 70 — Demo Readiness Plan (proposal)

Date: 2026-08-02
Status: Proposal, not yet started. This document is documentation output of the
Phase 69 audit — it does not itself change any code or config.

## Goal

Make the existing, already-solid ledger/reporting/AI-assistant product demoable to a
non-technical audience (prospective customer, investor, internal stakeholder) with a
single, reliable setup path and a compelling first-run experience — **without**
building any new accounting subledgers (invoices/customers/etc. are Phase 71+).

## Why this phase first

The Phase 69 audit found the core engine (chart of accounts, journal entries, fiscal
periods, reports, audit log, AI assistant) is functionally complete and well tested
(554 backend test functions), but three things block a good demo today:

1. No one-command local environment (no Docker Compose) — see `README.md`, which
   documents a manual Postgres + Alembic + Uvicorn + npm setup.
2. No seed/demo dataset — `backend/app/application/accounts/defaults.py` seeds a
   chart of accounts only; there's no seeded journal history to show working reports.
3. Unverified first-run UX (empty states, AI assistant behavior without API keys) and
   unverified `.env` secrets hygiene.

Fixing these is low-risk, high-leverage, and does not touch domain logic, auth, RBAC,
tenant scoping, rate limiting, transaction boundaries, or the DB schema — consistent
with the hard constraints for this audit and a sensible "first real phase" after it.

## Scope (in)

1. **Docker Compose for local/demo environment**
   - Add `docker-compose.yml` (and Dockerfiles for backend/frontend if not present)
     to bring up Postgres + backend + frontend with one command.
   - Files likely affected: new `docker-compose.yml`, new `backend/Dockerfile`, new
     `frontend/Dockerfile`, possibly a `.dockerignore` per service.
   - Must not change `backend/app` runtime behavior, only how it's packaged/run.

2. **Seed/demo data script**
   - A script (e.g. `scripts/seed_demo_data.py` or extend an existing script under
     `scripts/`) that creates a demo company, seeds the default chart of accounts
     (reusing `backend/app/application/accounts/defaults.py`), and posts a small set
     of realistic journal entries across a few months so reports and the dashboard
     have real numbers to show.
   - Must use existing use cases (`CreateJournalEntry`, `PostJournalEntry`, etc.) via
     the application layer — not raw SQL — to stay consistent with the tested
     lifecycle and avoid bypassing validation.
   - Files likely affected: new script under `scripts/`, no changes to
     `backend/app/application` or `backend/app/modules` logic itself.

3. **First-run UX verification pass (read-only audit + tiny fixes only)**
   - Manually walk dashboard, accounts, journal entries, all 5 report pages, audit
     logs, company users, settings with an empty and then a seeded company.
   - Fix only trivial, obvious issues (e.g., a broken doc link, a typo) per the hard
     constraints — anything larger becomes a Phase 70 follow-up ticket, not an inline
     fix.
   - Files likely affected: none, or a one-line typo/link fix at most.

4. **AI assistant demo readiness**
   - Document (not change) how to configure `GEMINI_API_KEY`/`OPENAI_API_KEY` for a
     live demo of the LLM-backed assistant, and confirm/document the rules-fallback
     behavior is acceptable as the default demo mode when no key is set (already true
     per `backend/app/modules/accounting/services/ai_provider_factory.py`).
   - Files likely affected: documentation only (e.g., a demo runbook).

5. **Secrets hygiene check**
   - Verify `backend/.env` and `frontend/.env` are excluded by `.gitignore` and were
     never committed to history. This is a read-only verification step; if a problem
     is found, it should be escalated, not silently fixed by an agent mid-phase.

6. **README / demo script**
   - Add a short "Run the demo" section to `README.md` (or a new
     `docs/product/demo-runbook.md`) describing: `docker-compose up`, run seed script,
     login with demo credentials, walk through dashboard → accounts → journal entries
     → reports → AI assistant.

## Scope (out — do NOT touch in Phase 70)

- No invoices, customers, suppliers, payments, bank accounts/transactions, or VAT/tax
  (these are Phase 71+).
- No auth/RBAC/tenant-scoping/rate-limiting/transaction-boundary changes.
- No DB schema changes or Alembic migrations.
- No UI redesign — only fixing genuinely broken states found during the walkthrough.
- No changes to the AI provider logic itself, only documentation of how to configure
  it for a demo.
- Do not commit `.env` files or real API keys anywhere.

## Safe implementation order

1. Secrets hygiene check (read-only, do first — blocks nothing else but must be
   confirmed clean before public demo).
2. Docker Compose + Dockerfiles (infra-only, no app code changes).
3. Seed/demo data script (uses existing tested use cases only).
4. First-run UX walkthrough with seeded data; log findings; fix only trivial issues
   inline, file follow-up tickets for anything larger.
5. AI assistant demo documentation.
6. README / demo runbook update.

## Validation commands

Run from repo root unless noted.

```bash
# Backend test suite (must stay green — no application logic should change)
cd backend && python -m pytest

# Backend static validation (mirrors CI)
cd backend && python -m pyflakes app  # or whatever linter CI uses — confirm against
                                       # .github/workflows/backend-validation.yml

# Frontend type-check and lint (mirrors CI)
cd frontend && npx tsc -b --noEmit
cd frontend && npm run lint

# Frontend unit/architecture tests
cd frontend && npm run test

# New: bring up the demo stack
docker-compose up --build

# New: seed demo data (after stack is up and migrations have run)
python scripts/seed_demo_data.py   # exact path/name TBD during implementation
```

## Acceptance criteria

- `docker-compose up` (or documented equivalent) brings up Postgres + backend +
  frontend with zero manual steps beyond copying `.env.example` to `.env`.
- A seed script produces a demo company with a populated chart of accounts and at
  least one full month of posted journal entries, visible correctly in the dashboard
  and all 5 report pages (trial balance, P&L, balance sheet, account ledger, general
  ledger).
- All existing backend tests (554 functions) and frontend checks (`tsc -b`,
  `eslint`, `vitest`) still pass unchanged — Phase 70 must not regress anything.
- The AI assistant demo path is documented, including the expected (safe) fallback
  behavior when no LLM API key is configured.
- `backend/.env` and `frontend/.env` are confirmed excluded from git tracking (or a
  remediation plan is raised if they are not).
- README (or a new demo runbook doc) gives a first-time reader a working demo in
  under 10 minutes, start to finish.

## Expected deliverable

- `docker-compose.yml` + service Dockerfiles for one-command local demo.
- A demo seed-data script using existing, tested application use cases.
- A short demo runbook (README section or `docs/product/demo-runbook.md`).
- A short written list of any first-run UX issues found (for triage into Phase 70
  follow-ups or Phase 71+), even if not all are fixed in this phase.
- Confirmation (or remediation ticket) on `.env` secrets hygiene.

## Risk

Low. All work is additive (new Docker/scripts/docs files) or read-only verification.
The only way this phase introduces risk is if seed-data scripts bypass application
use cases and write directly to the database — this must be avoided; seed scripts
should call the same `CreateJournalEntry`/`PostJournalEntry`/etc. use cases that
production code and tests already exercise.
