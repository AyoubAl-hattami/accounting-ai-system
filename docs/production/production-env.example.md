# Production environment reference

This is a configuration contract, not an `.env` file. It contains no usable
secret. Store production secrets in the selected platform's secret manager and
inject them at runtime. Never commit a populated `.env`, frontend build output,
database dump, provider key, token, tunnel log, or backup.

Production and staging configuration must be reviewed together with the deployment artifact.
Phase 77B enforces the application settings in this reference at backend startup
and guards the frontend production build. Infrastructure-owned controls below
still require operator and hosting-provider verification.

## Backend runtime variables

| Variable | Required | Production requirement |
|---|---:|---|
| `APP_ENV` | Yes | Exactly `production`. Enables the current secret-key guard and blocks demo/cleanup scripts. |
| `APP_NAME` | Yes | Customer-facing service name; non-secret. |
| `APP_VERSION` | Yes | Immutable release/tag identifier, not a mutable label such as `latest`. |
| `APP_PUBLIC_URL` | Yes | Public HTTPS frontend origin, no path or trailing slash, for example `https://ledger.example.invalid`. Never localhost. |
| `DATABASE_URL` | Yes, secret | PostgreSQL SQLAlchemy URL for a dedicated least-privilege application role. Require encrypted transport according to the provider, commonly `sslmode=require` or stricter certificate validation. Never SQLite. |
| `SECRET_KEY` | Yes, secret | Unique high-entropy JWT signing key. Current startup requires at least 32 characters; use at least 64 random bytes/URL-safe output and define rotation/session invalidation. Never reuse development, CI, or another environment's key. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | Must be explicitly set. Use 15-60 minutes. Values over 60 require `PRODUCTION_ALLOW_LONG_LIVED_TOKENS=true` and recorded risk acceptance. |
| `PRODUCTION_ALLOW_LONG_LIVED_TOKENS` | No | Defaults to `false`. Temporary exception only; it does not fix browser token storage or session architecture. |
| `PUBLIC_REGISTRATION_ENABLED` | No | Must be unset or `false` in production. Production startup rejects `true`; client admins are created by platform onboarding. |
| `PRODUCTION_ALLOW_LOCAL_DATABASE` | No | Defaults to `false`. Set only for an explicitly accepted single-host topology; managed remote PostgreSQL is preferred. |
| `PRODUCTION_ALLOW_DATABASE_WITHOUT_TLS` | No | Defaults to `false`. Production requires `sslmode=require`, `verify-ca`, or preferably `verify-full`; override only for a documented private/single-host exception. |
| `PRODUCTION_SUBSCRIPTION_FAIL_CLOSED` | No | Defaults to `true` and production startup rejects `false`. A missing subscription blocks business APIs. |
| `ALGORITHM` | No | Application is intentionally restricted to `HS256`; do not override. |
| `CORS_ORIGINS` | Yes | Comma-separated exact HTTPS frontend origins. No `*`, localhost, HTTP, path, or trailing wildcard. Include only origins that must call the API directly. |
| `AUTH_FAILED_LOGIN_LIMIT` | Yes | Positive limit approved with shared/edge rate limiting. Suggested starting policy: 5. |
| `AUTH_FAILED_LOGIN_WINDOW_SECONDS` | Yes | Positive window. Suggested starting policy: 300 seconds, tuned with monitoring. |
| `AUTH_REGISTER_RATE_LIMIT` | Conditional | Required only if registration remains enabled; registration should be disabled or invitation-gated before launch. |
| `AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS` | Conditional | Same boundary as registration limit. |
| `AI_JOURNAL_PROVIDER` | Yes | One approved value: `rules`, `openai`, or `gemini`. Production startup rejects any other value and requires the selected external provider key. Use `rules` until privacy and commercial review is complete. |
| `OPENAI_API_KEY` | Conditional, secret | Required only when approved provider is `openai`; otherwise unset. Restrict, monitor, and rotate it. |
| `OPENAI_MODEL` | Conditional | Pin the approved model identifier when using OpenAI; validate changes before deployment. |
| `GEMINI_API_KEY` | Conditional, secret | Required only when approved provider is `gemini`; otherwise unset. Restrict, monitor, and rotate it. |
| `GEMINI_MODEL` | Conditional | Pin the approved model identifier when using Gemini; validate changes before deployment. |

Recommended secret generation for local operator use (the generated value must
go directly into the secret manager, not documentation or shell history):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Frontend build-time variables

Vite embeds `VITE_*` values into public JavaScript. They are never secrets.
Changing one requires a new frontend build.

| Variable | Required | Production requirement |
|---|---:|---|
| `VITE_API_BASE_URL` | Yes | Prefer same-origin `/api`; otherwise use the exact public HTTPS API origin. If omitted, the current code falls back to `http://127.0.0.1:8010`, which is invalid for customers. |
| `VITE_PUBLIC_DEMO` | No | Must be unset or `0`. `1` is only for the temporary local Cloudflare demo workflow. |
| `VITE_PUBLIC_DEMO_ALLOWED_HOSTS` | No | Must be unset in production. |
| `VITE_DEV_API_PROXY_TARGET` | No | Development-server setting; must be unset in the production static build. |

## Illustrative non-secret shape

Values below use reserved/example domains and placeholders. Do not deploy them.

```env
APP_ENV=production
APP_NAME=Accounting AI System
APP_VERSION=<release-tag-or-commit>
APP_PUBLIC_URL=https://ledger.example.invalid

DATABASE_URL=<secret-manager-reference-to-postgresql-url>
SECRET_KEY=<secret-manager-reference-to-random-signing-key>
ACCESS_TOKEN_EXPIRE_MINUTES=<approved-short-duration>
PRODUCTION_ALLOW_LONG_LIVED_TOKENS=false
PUBLIC_REGISTRATION_ENABLED=false
PRODUCTION_ALLOW_LOCAL_DATABASE=false
PRODUCTION_ALLOW_DATABASE_WITHOUT_TLS=false
PRODUCTION_SUBSCRIPTION_FAIL_CLOSED=true

CORS_ORIGINS=https://ledger.example.invalid
AUTH_FAILED_LOGIN_LIMIT=5
AUTH_FAILED_LOGIN_WINDOW_SECONDS=300
AUTH_REGISTER_RATE_LIMIT=1
AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS=3600

AI_JOURNAL_PROVIDER=rules
OPENAI_API_KEY=
OPENAI_MODEL=<approved-model-if-used>
GEMINI_API_KEY=
GEMINI_MODEL=<approved-model-if-used>
```

Frontend build environment:

```env
VITE_API_BASE_URL=/api
VITE_PUBLIC_DEMO=0
```

## Infrastructure-owned configuration

These settings are not read by the application today but are mandatory parts of
the production deployment:

- DNS ownership, TLS certificates/renewal, HTTPS redirect, HSTS, CSP,
  `X-Content-Type-Options`, frame-ancestor policy, and referrer policy.
- Reverse proxy `/api` routing, SPA history fallback, body/time limits, trusted
  proxy network, request ID, and real-client-IP handling.
- API worker/process count, graceful shutdown, restart policy, health/readiness
  probes, CPU/memory limits, and deployment timeout.
- PostgreSQL region, version, TLS verification, least-privilege roles, connection
  and statement timeouts, pool limits, maintenance window, storage alerts, and
  point-in-time recovery.
- Encrypted backup schedule, retention, immutable/off-site copy, restore drill,
  RPO/RTO, and named restore owner.
- Central log destination, redaction policy, retention, error tracking, metrics,
  uptime checks, alert thresholds, and on-call contacts.
- Secret rotation owners and dates, dependency/SBOM scanning, release signing,
  incident response, rollback artifact, and migration recovery procedure.

## Preflight checks

Before every production start or deploy:

```powershell
python backend/scripts/production_preflight.py --mode staging
python backend/scripts/production_preflight.py --mode production
```

Run only the command matching the target environment after its variables have
been injected by the secret manager. The command prints pass/fail check names,
never configured values. A failed check blocks the deployment.

1. Confirm no value contains `localhost`, `127.0.0.1`, demo credentials, CI keys,
   reserved example placeholders, or temporary tunnel domains.
2. Confirm `APP_PUBLIC_URL`, `CORS_ORIGINS`, and `VITE_API_BASE_URL` agree with
   the intended HTTPS topology.
3. Confirm `DATABASE_URL` identifies PostgreSQL and the production database, uses
   encrypted transport, and does not grant owner/superuser privileges.
4. Confirm external AI keys are absent when `AI_JOURNAL_PROVIDER=rules`; when an
   external provider is selected, confirm legal approval and a successful
   secret-manager health check.
5. Run CI, secret/dependency scans, `alembic heads`, migration preflight, backup,
   deployment smoke tests, and record the release/version/migration identifiers.

## Forbidden production actions

- Do not run `scripts/seed_demo_data.py`, `scripts/cleanup_local_demo_data.py`,
  `scripts/reset_company_data.py`, `restore_admin.py`, or public-demo tunnel scripts.
- Do not run Uvicorn with `--reload`, Vite dev/preview as the public web server,
  or Cloudflare Quick Tunnel as production hosting.
- Do not copy the development database into production.
- Do not create or promote platform owners with ad hoc SQL. Use the confirmed
  `scripts/bootstrap_platform_admin.py` workflow in the handover runbook.
- Do not send temporary passwords to logs, tickets, analytics, source control,
  shared documents, or long-lived terminal captures.
