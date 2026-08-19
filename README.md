# Accounting AI System

Accounting AI System is a full-stack, multi-tenant accounting SaaS engineering
project built with FastAPI, PostgreSQL, React, TypeScript, and a substantial set
of production-readiness documentation. It brings together platform
administration, client onboarding, subscriptions, a custom chart of accounts,
journal workflows, financial reporting, AI assistant memory, tenant security
boundaries, and explicit production-readiness gates.

This public repository is shared as a portfolio / engineering showcase. It is
not marked as a final commercial production deployment: external deployment,
backup, monitoring, legal, and operational gates must be completed and approved
before real customer use.

> **Project status:** Full-stack accounting SaaS foundation with
> production-readiness gates.

## Production status

This repository has production-readiness gates and deployment runbooks, but the
final production gate remains **NO-GO** until real staging evidence, DNS/TLS,
managed PostgreSQL, secret-manager integration, a backup/restore drill,
monitoring, legal/privacy/accounting approvals, and customer handover sign-off
are completed.

See the [production-readiness audit](docs/production/production-readiness-audit.md)
and [final production gate](docs/production/final-production-gate.md) for the
authoritative status and outstanding evidence.

## Features

- Multi-tenant company model
- Platform admin and client admin separation
- Client onboarding flow
- Subscription management
- Custom chart of accounts
- Fiscal years and periods
- Journal entry workflow
- Double-entry validation
- Reversal entries
- Opening balances
- Trial Balance
- Profit and Loss
- Balance Sheet
- General Ledger
- Account Ledger
- Audit logs
- AI assistant with scoped conversation memory
- Local demo workflow
- Production-readiness docs and gates

## What this project demonstrates

- SaaS boundaries and secure tenant-access patterns
- Accounting domain modeling and double-entry invariants
- Explicit workflow and state transitions
- Production-readiness thinking and operational runbooks
- AI feature scoping with user, company, and conversation memory boundaries
- Full-stack implementation discipline across API, database, UI, testing, and operations

## Tech stack

### Backend

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Pydantic v2
- JWT authentication
- pytest

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Vitest

### Operations / production readiness

- Docker/Compose reference templates
- Nginx/Caddy reference topology
- Production preflight checks
- Backup/restore runbooks
- Monitoring and incident runbooks
- Deployment and rollback documentation

## Repository status

- Public portfolio repository and engineering showcase
- Not a final commercial production deployment
- Contains no real customer data
- Production secrets and `.env` files must never be committed
- Local demo credentials are development-only and must never be reused in production

## Validation snapshot

The latest documented production-readiness phase records that:

- The backend suite passed in the latest production-readiness phase
- Frontend TypeScript, production build, and Vitest passed in the latest production-readiness phase
- Alembic one-head validation passed
- Staging and external production gates remain pending

This snapshot is historical evidence, not a substitute for running validation on
new changes. Docker Compose execution is not claimed here; the deployment files
are reference templates pending real staging verification.

## Quick local demo

> **Local demo only.** The demo uses documented development credentials and
> seeded sample data. Never use those credentials, seed data, or scripts in a
> production environment.

Follow the [local demo quickstart](docs/demo/local-demo-quickstart.md) for the
credentials, prerequisites, expected report figures, walkthrough, and
troubleshooting. From the repository root, the main workflow is:

```powershell
.\scripts\dev-start-backend.ps1     # migrations + API on 127.0.0.1:8010
.\scripts\dev-seed-demo.ps1         # idempotent local sample data
.\scripts\dev-start-frontend.ps1    # Vite on 127.0.0.1:5173
```

The optional [local demo tunnel](docs/demo/free-public-local-demo-tunnel.md)
provides a temporary public link for demonstrating a local instance. It is not
production hosting. If sample data needs removal, use the dry-run-first
[local demo cleanup workflow](docs/demo/local-demo-cleanup.md).

## Manual backend setup

### Prerequisites

- Python and `pip`
- PostgreSQL
- A database named in `DATABASE_URL`

Create and activate a virtual environment, then install dependencies:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy the development environment template:

```powershell
copy .env.example .env
```

At minimum, configure a local PostgreSQL `DATABASE_URL` and generate a unique
development `SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Do not commit `backend/.env`. Apply migrations and start the API:

```powershell
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

Useful local endpoints:

- API documentation: <http://127.0.0.1:8010/docs>
- Application health: <http://127.0.0.1:8010/health>
- Database health: <http://127.0.0.1:8010/health/db>

Run backend validation from `backend/` after PostgreSQL and the required test
environment are available:

```powershell
$env:PYTHONPATH = (Get-Location).Path
pytest tests -v
```

See the [backend validation runbook](docs/backend-validation-runbook.md) for the
database prerequisites, migration checks, and complete validation workflow.

## Manual frontend setup

Install dependencies and start Vite:

```powershell
cd frontend
npm install
npm run dev
```

The frontend is available at <http://127.0.0.1:5173>. Copy
`frontend/.env.example` to `frontend/.env` only when you need to override the
local API URL.

Run frontend validation with:

```powershell
npm run lint
npm run build
npm run test:run
```

## Accounting workflow

Journal entries move through an explicit workflow:

```text
draft -> reviewed -> posted
```

- Draft entries can be updated, reviewed, or voided.
- Draft or reviewed entries can be posted when validation succeeds.
- Posted entries are immutable and corrected through reversal entries.
- Double-entry validation requires balanced debit and credit totals.
- Financial reports are scoped by authenticated company access.

The reporting surface includes Trial Balance, Profit and Loss, Balance Sheet,
General Ledger, and Account Ledger views.

## Security boundaries

- Tenant accounting access is scoped through company membership and roles.
- Platform administrators use a separate control plane and cannot enter tenant
  accounting routes as a shortcut.
- AI conversation memory is scoped by company, user, and conversation.
- Production settings fail closed around secrets, public URLs, CORS, database
  configuration, and other deployment controls documented in the audit.
- Local credentials and sample identities are prohibited in production.

These controls support a production-oriented architecture; they do not replace
the external evidence and approvals required by the final production gate.

## Production documentation

- [Production-readiness audit](docs/production/production-readiness-audit.md)
- [Production environment reference](docs/production/production-env.example.md)
- [Deployment runbook](docs/production/deployment-runbook.md)
- [Backup and restore runbook](docs/production/backup-restore-runbook.md)
- [Monitoring and incident runbook](docs/production/monitoring-incident-runbook.md)
- [Migration and rollback runbook](docs/production/migration-rollback-runbook.md)
- [Production data initialization](docs/production/production-data-initialization.md)
- [Final production gate](docs/production/final-production-gate.md)

Production deployment requires dated staging evidence, named approvers, and a
GO decision under these documents.

## Project structure

```text
accounting-ai-system/
|-- backend/                              # FastAPI application, migrations, tests
|-- frontend/                             # React and TypeScript application
|-- docs/                                 # Product, architecture, demo, and operations docs
|-- deploy/production/                    # Reverse-proxy reference configuration
|-- scripts/                              # Local demo and operational helpers
|-- docker-compose.production.example.yml # Production topology reference
`-- README.md
```

## Scope note

This repository demonstrates an accounting SaaS foundation and its
production-readiness gates. It does not claim tax compliance, legal approval,
completed bank reconciliation or payroll capabilities, or final commercial
production readiness.
