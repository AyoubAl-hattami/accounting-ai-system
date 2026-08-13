# Migration and rollback runbook

Status: execution template. Database restore is a controlled last-resort decision.

## Pre-deploy gate

1. Record the immutable release tag, commit, image digests, prior release, operator,
   change ticket, database engine/version, and planned maintenance window.
2. Require green CI and review every migration between the deployed and target tags
   for data loss, table rewrites, locks, backfills, defaults, and downgrade fidelity.
3. From the release artifact, run `alembic heads` and require exactly one head.
4. Against staging, run `alembic current` and record the revision. Do not infer it
   from source files.
5. Verify a pre-deploy backup and recoverable restore point. Record the backup ID,
   checksum, retention, and successful-job evidence.
6. Confirm the previous application artifact and its compatible configuration are retained.

## Deploy and migrate

```powershell
alembic heads
alembic current
alembic upgrade head
alembic current
```

Run the migration once as a controlled task, never concurrently in worker startup.
Capture exit codes and timestamps without connection strings. Start the immutable
application artifact, then execute `staging-smoke-test.md` and reconcile key counts
and accounting reports.

## Rollback decision

1. Stop or drain writes when data consistency may be affected.
2. Preserve logs, the failed database, and a failure-point backup.
3. Prefer rolling back only the application artifact when the new schema is backward
   compatible. Verify with the prior release's documented compatibility range.
4. Use `alembic downgrade` only after migration-specific review proves it is safe and
   preserves all required data. Never downgrade reflexively during an incident.
5. When schema/data rollback is unsafe, restore the pre-deploy backup into an isolated
   database, reconcile it, calculate the data-loss window, and obtain incident owner
   plus business approval before switching traffic.
6. Repeat health, authorization, accounting reconciliation, and customer-impact checks.

Record the decision owner, timeline, achieved recovery time, lost/replayed writes,
customer communications, and follow-up actions. An untested written rollback plan
does not satisfy the final production gate.
