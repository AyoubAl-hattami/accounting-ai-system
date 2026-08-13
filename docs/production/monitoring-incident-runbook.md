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

## Alert ownership and severity

| Signal | Initial severity | Required owner/action |
|---|---|---|
| Public HTTPS or frontend unavailable | Sev 1 when sustained | On-call operations; validate edge, app, and customer impact |
| API 5xx rate above approved threshold | Sev 2, Sev 1 if broad outage/data risk | Backend on-call; correlate release and request IDs |
| Failed-login or invitation abuse spike | Sev 2 | Security owner; inspect source, shared limits, and account targeting |
| Database connection saturation or storage critical | Sev 1/2 | Database owner; protect writes and capacity |
| Migration failure/schema mismatch | Sev 1 during deploy | Release owner; stop rollout and use rollback gate |
| Backup missed, corrupt, or older than RPO | Sev 1 | Backup owner; restore coverage is not assumed |
| Missing/unmanaged or anomalous subscriptions | Sev 2 | SaaS operations; reconcile without exposing tenant state |
| External AI error/latency/cost breach | Sev 2 | AI owner; disable provider or fall back only under approved policy |

Thresholds, evaluation windows, notification routes, primary/secondary owners,
acknowledgement targets, and escalation times must be filled in the monitoring
platform and tested. Avoid alert storms by grouping on service and incident.

## Incident timeline template

| UTC time | Actor | Observation/action | Evidence/decision |
|---|---|---|---|
| `<time>` | `<role>` | Detection and initial scope | `<restricted link>` |
| `<time>` | `<role>` | Severity and incident commander assigned | `<decision>` |
| `<time>` | `<role>` | Containment/recovery action | `<result>` |
| `<time>` | `<role>` | Customer/legal notification decision | `<approver>` |
| `<time>` | `<role>` | Service and data reconciliation complete | `<evidence>` |

## Customer communication template

> We are investigating an issue affecting `<confirmed service or workflow>` from
> `<confirmed start time>`. Current verified impact is `<facts only>`. We have
> `<confirmed containment or investigation action>`. The next update is scheduled
> for `<time>`. Please use `<approved support channel>` for urgent cases.

Do not speculate about cause, data access, data loss, recovery time, liability,
or regulatory impact. Security/privacy statements require the incident commander
and legal/privacy decision owner.

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
