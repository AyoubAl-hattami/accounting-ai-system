# Monitoring and incident runbook

Status: required controls defined; vendor implementation and alert evidence pending.

## Minimum monitoring

- External HTTPS uptime and latency for the SPA and `/api/health`.
- Internal database readiness from `/health/db`; do not expose it publicly unless protected.
- API 5xx rate, latency percentiles, worker restarts, CPU/memory, and queue/pool pressure.
- Failed-login and registration/invitation spikes using redacted structured events.
- PostgreSQL connections, locks, replication/PITR status, storage growth, and capacity.
- Backup completion, age, checksum, retention, and restore-drill age.
- Migration job failure and application/schema revision mismatch.
- Missing/unmanaged subscriptions, expiry anomalies, and unexpected status transitions.
- External AI error/rate/latency/cost signals when OpenAI or Gemini is approved.
- TLS expiry, DNS changes, secret age, dependency/security alerts, and disk capacity.

Alerts must route to a named human, have severity and response targets, avoid
password/token/financial payloads, and be tested from trigger through receipt.
Process-local authentication limiting is insufficient across workers; configure
shared edge/WAF or Redis-backed limits before pilot.

## Incident flow

1. Acknowledge, assign incident commander, severity, timestamp, and secure channel.
2. Preserve logs/audit data and identify affected tenants, data, versions, and window.
3. Contain: revoke credentials/sessions, disable provider integrations, restrict
   traffic, or enter maintenance mode without deleting evidence.
4. Recover through the deployment and backup runbooks; reconcile accounting data.
5. Notify customers/regulators according to approved legal breach timelines.
6. Monitor recurrence, close only with owner approval, and publish an appropriate summary.
7. Complete a blameless review with root cause, control gaps, actions, owners, and dates.

Never paste secrets, tokens, passwords, raw AI prompts, or full accounting payloads
into logs, alerts, chat, or tickets. Use request IDs and tenant/user IDs with access controls.

## Objective GO evidence

- Dashboard links and alert inventory with owners and thresholds.
- Test alerts received for uptime, 5xx, failed login, DB capacity, backup failure,
  migration failure, subscription anomaly, and AI failure where applicable.
- Current on-call rota, severity matrix, customer communication templates, and
  one tabletop incident/rollback exercise with recorded actions.
