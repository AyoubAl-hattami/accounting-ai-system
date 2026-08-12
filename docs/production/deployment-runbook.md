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

The compose file is an example, not an unattended production deployment. Set
`APP_DOMAIN` to a DNS name already pointed at the host and permit ports 80/443 so
Caddy can obtain certificates. It deliberately does not create PostgreSQL or
contain credentials. FastAPI's broad forwarded-header trust is safe only while
the backend remains unpublished on the private Compose network.

## Release procedure

1. Select an immutable signed commit/tag and require green backend/frontend CI.
2. Build images from that revision. Record image digests and dependency scan results.
3. Provision a new empty PostgreSQL database, least-privilege application role,
   TLS verification, point-in-time recovery, and storage alerts. Never copy the local DB.
4. Inject reviewed secrets and settings from a secret manager. Do not create a
   tracked `production.env`; the example compose reference is operator-owned.
5. Take/verify the pre-deploy backup and record the restore target and operator.
6. Run `alembic heads` and require one head. Review migration locks and downgrade.
7. Run `alembic upgrade head` once as a controlled task, never in every worker startup.
8. Start backend and frontend images. Verify internal `/health` and `/health/db`.
9. Configure public DNS/TLS, HTTPS redirect, HSTS, body/time limits, request IDs,
   trusted proxy ranges, WAF/shared rate limits, and log redaction at the edge.
10. Smoke-test `/api/health`, direct SPA route refresh, login, password change,
    platform dashboard, onboarding, tenant isolation, subscription lockout,
    journals, reports, export, Arabic/RTL, and mobile.
11. Run the manual QA checklist in `production-readiness-audit.md` and record sign-off.

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
