# Production deployment runbook

Status: repository template complete; real infrastructure and staging evidence pending.

## Supported topology

The reference topology is Caddy at the public edge, an immutable React static
build served by internal Nginx, a multi-worker internal FastAPI container, and
an external managed PostgreSQL database. Caddy owns the public domain, automatic
TLS/renewal, HTTPS redirects, HSTS, and forwarding to Nginx. Nginx serves SPA
history fallback and proxies `/api/*` to FastAPI. Only Caddy publishes host ports.

Repository artifacts:

- `backend/Dockerfile`
- `frontend/Dockerfile` and `frontend/nginx.production.conf`
- `docker-compose.production.example.yml`
- `deploy/production/Caddyfile`
- `production-env.example.md`
- `staging-smoke-test.md`
- `migration-rollback-runbook.md`
- `production-data-initialization.md`
- `final-production-gate.md`

The compose file is an example, not an unattended production deployment. Set
`APP_DOMAIN` to a DNS name already pointed at the host and permit ports 80/443 so
Caddy can obtain certificates. It deliberately does not create PostgreSQL or
contain credentials. FastAPI's broad forwarded-header trust is safe only while
the backend remains unpublished on the private Compose network.

## Release procedure

1. Select an immutable signed commit/tag and require green backend/frontend CI.
2. Load the candidate settings from the staging or production secret manager and
   run `python backend/scripts/production_preflight.py --mode staging` (or
   `--mode production`). A nonzero exit blocks deployment; output contains check
   names only and must not be changed to print values.
3. Build images from that revision. Record image digests and dependency scan results.
4. Provision a new empty PostgreSQL database, least-privilege application role,
   TLS verification, point-in-time recovery, and storage alerts. Never copy the local DB.
5. Inject reviewed secrets and settings from a secret manager. Do not create a
   tracked `production.env`; the example compose reference is operator-owned.
6. Take/verify the pre-deploy backup and record the restore target and operator.
7. Follow `migration-rollback-runbook.md`; require one Alembic head and review locks.
8. Run `alembic upgrade head` once as a controlled task, never in every worker startup.
9. Start backend and frontend images. Verify internal `/health` and `/health/db`.
10. Configure public DNS/TLS, HTTPS redirect, HSTS, body/time limits, request IDs,
   trusted proxy ranges, WAF/shared rate limits, and log redaction at the edge.
11. Complete and sign `staging-smoke-test.md`, including browser proof that API
    calls never target localhost and direct SPA route refresh succeeds.
12. Run the manual QA checklist in `production-readiness-audit.md` and record sign-off.

The frontend container uses Nginx static serving; Vite dev/preview is forbidden.
The backend uses multi-worker Uvicorn without `--reload`. Caddy is the only
published service. Keep FastAPI's `--forwarded-allow-ips=*` only while both backend
and frontend ports remain private to the Compose network. For any other topology,
replace it with explicit trusted proxy addresses before accepting traffic.

The reference Nginx limits request bodies and header/body/connect/read/write
timeouts. Tune values against tested exports and imports; do not remove bounds.
CSP currently permits inline styles required by the frontend and must be verified
against the built application. HSTS `includeSubDomains` is appropriate only when
every subdomain is HTTPS-capable; add `preload` only after meeting browser preload
requirements and obtaining infrastructure-owner approval.

## Platform owner bootstrap

Set `PLATFORM_ADMIN_EMAIL`, `PLATFORM_ADMIN_NAME`, and preferably
`PLATFORM_ADMIN_TEMPORARY_PASSWORD` through the secret manager, then run once:

```powershell
python scripts/bootstrap_platform_admin.py --confirm BOOTSTRAP
```

To generate a password, add `--generate-password`; it is not printed unless
`--show-temporary-password` is also explicitly supplied. Store any displayed
value once in the approved handover channel, then clear terminal capture. An
existing non-superuser requires `--promote`; an existing superuser is left
unchanged. The client must change the temporary password immediately.

## Rollback

1. Stop traffic or place writes in maintenance mode.
2. Preserve logs and take a failure-point backup before any recovery action.
3. Roll application images back by immutable digest when the schema remains compatible.
4. Never run an Alembic downgrade before reviewing data loss and lock behavior.
5. If schema rollback is unsafe, restore the pre-deploy backup to an isolated DB,
   reconcile it, switch credentials/traffic under an approved incident plan, and
   retain the failed database for investigation.
6. Record timeline, versions, migration revisions, data checks, approvers, and outcome.

## Objective GO evidence

- Public HTTPS staging deployment from a tagged commit with no manual image edits.
- TLS/security-header report, exact CORS evidence, and no browser localhost calls.
- One-head migration log, platform bootstrap audit row, and completed smoke results.
- Successful application and database rollback rehearsal with measured duration.
- Named production operator, secrets owner, on-call contact, and approved change record.
