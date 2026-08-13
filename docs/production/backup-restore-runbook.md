# PostgreSQL backup and restore runbook

Status: template only. C5 remains pending until a witnessed restore drill succeeds.

## Required decisions

The accountable owner must approve numeric targets before GO:

- RPO: `<maximum acceptable data loss in minutes>`
- RTO: `<maximum acceptable recovery time in minutes>`
- Backup frequency/retention: `<schedule and retention tiers>`
- Regions and immutable/off-site copy: `<locations>`
- Backup owner and restore approver: `<named roles>`

Use provider point-in-time recovery plus encrypted logical backups where supported.
Backups must be encrypted in transit/at rest, access-controlled, monitored, and
restored regularly. A successful backup job alone is not recovery evidence.

## Command templates

Use secret-manager-injected `DATABASE_URL`; never paste it into this document or logs.

```powershell
$backupFile = "<approved-encrypted-volume>\accounting-<UTC-timestamp>.dump"
pg_dump --dbname $env:BACKUP_DATABASE_URL --format=custom --no-owner --no-acl --file $backupFile
Get-FileHash -Algorithm SHA256 -LiteralPath $backupFile
pg_restore --list $backupFile

# RESTORE_DATABASE_URL must identify a new, isolated drill database.
pg_restore --dbname $env:RESTORE_DATABASE_URL --no-owner --no-acl --exit-on-error $backupFile
```

`BACKUP_DATABASE_URL` and `RESTORE_DATABASE_URL` are secret-manager-injected and
must never be echoed. The backup path is a mounted encrypted destination, not
source control or the application container filesystem. `RESTORE_DATABASE_URL`
must point to a newly provisioned empty isolated drill database,
never the active production database. Verify checksums before restore and securely
remove temporary plaintext material according to the retention policy.

## Restore drill

1. Open a change/drill record with backup ID, timestamps, operators, and target RPO/RTO.
2. Provision an isolated PostgreSQL version compatible with production.
3. Restore the selected backup and record start/end time and all command exit codes.
4. Run `alembic current` and compare it with the release migration revision.
5. Compare counts for companies, users, memberships, subscriptions, accounts,
   fiscal periods, journal entries/lines, audit logs, and AI conversations.
6. For accountant-approved sample tenants, reconcile trial balance debits/credits,
   balance sheet equation, profit/loss, general ledger, account running balance,
   posted/reversed entry counts, and export generation.
7. Confirm tenant isolation and login only with drill-specific rotated credentials.
8. Record missing/corrupt rows, duration, achieved RPO/RTO, and approver sign-off.
9. Destroy the isolated restore under provider policy after evidence is retained.

Record source and restore counts in a restricted worksheet. Query aggregates only:

```sql
SELECT 'companies' AS entity, COUNT(*) FROM companies
UNION ALL SELECT 'users', COUNT(*) FROM users
UNION ALL SELECT 'company_users', COUNT(*) FROM company_users
UNION ALL SELECT 'subscriptions', COUNT(*) FROM company_subscriptions
UNION ALL SELECT 'accounts', COUNT(*) FROM accounts
UNION ALL SELECT 'journal_entries', COUNT(*) FROM journal_entries
UNION ALL SELECT 'journal_lines', COUNT(*) FROM journal_lines;
```

The drill must also record the `alembic_version` row and compare accountant-approved
report totals for representative tenants. Row counts alone do not prove ledger integrity.

## Migration and deployment recovery checklist

- [ ] Pre-migration backup and restore point verified.
- [ ] Upgrade/downgrade reviewed for destructive operations and long locks.
- [ ] Previous application image and configuration revision retained.
- [ ] Forward-fix versus downgrade decision owner named.
- [ ] Writes stopped before database point-in-time recovery.
- [ ] Restored data reconciled before traffic switches.
- [ ] Customer/incident communication timeline recorded.

## Objective GO evidence

A dated restore-drill record must identify the real backup, isolated destination,
commands, row/report reconciliations, achieved RPO/RTO, defects, and operations plus
business-owner approval. Until then C5 is open and production remains NO-GO.
