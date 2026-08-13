# Production data initialization

Production must start with a newly provisioned empty PostgreSQL database. Never
copy a local/demo database, run `seed_demo_data.py`, use cleanup/reset scripts, or
promote an owner through ad hoc SQL.

## Controlled sequence

- [ ] Provision PostgreSQL with TLS, least-privilege application and migration
      roles, backups/PITR, capacity alerts, and no imported application rows.
- [ ] Record `alembic heads`, apply `alembic upgrade head` once, and record
      `alembic current`.
- [ ] Before bootstrap, verify zero rows in `users`, `companies`, `company_users`,
      `company_subscriptions`, `accounts`, and `journal_entries`.
- [ ] Run `scripts/bootstrap_platform_admin.py --confirm BOOTSTRAP` using identity
      and password inputs injected by the approved secret/handover channel.
- [ ] Reject `admin@example.com`, `Password123`, documented demo identities, and
      any credential reused from development or CI.
- [ ] Verify exactly the intended platform owner exists, `is_superuser` is true,
      and `must_change_password` is true. Do not add the owner to a client company.
- [ ] Sign in over HTTPS, change the temporary password, verify the original token
      is rejected, and retain only non-secret audit evidence.
- [ ] Re-run zero-demo/test checks before onboarding the first customer.

Read-only verification queries must be reviewed against the deployed schema and
run with output restricted to counts. Do not export identity rows into tickets:

```sql
SELECT COUNT(*) FROM companies;
SELECT COUNT(*) FROM company_users;
SELECT COUNT(*) FROM accounts;
SELECT COUNT(*) FROM journal_entries;
SELECT COUNT(*) FROM users WHERE lower(email) LIKE '%@example.com';
```

Expected counts before bootstrap are zero. After bootstrap, only the approved
platform owner user count changes. Any unexpected row is a release blocker to
investigate, not an instruction to run the local cleanup script.
