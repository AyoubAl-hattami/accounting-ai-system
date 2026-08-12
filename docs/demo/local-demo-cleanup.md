# Local demo data cleanup

Use this workflow only for a local development database that has accumulated
automated-test companies and users. It is not part of application startup and
never runs automatically.

## Safety model

- `APP_ENV` must be exactly `development`; production, staging, and test are refused.
- The default is a dry run. It prints candidate companies, automated-test users,
  and dependent-row counts without changing the database.
- Deletion requires the explicit `--confirm` flag.
- Automatic candidates are restricted to the test factory email domain
  `@accounting-ai-test.dev`, companies wholly owned by those test identities,
  and known test-factory company-name prefixes.
- Platform superusers are never selected for deletion.
- A local company that does not match those rules can be included only by an
  explicit `--company-id`. Inspect the dry run before confirming.

## Dry run

From `backend`:

```powershell
.venv\Scripts\activate
$env:PYTHONPATH = "C:\ayoub\accounting-ai-system\backend"
$env:APP_ENV = "development"
python scripts/cleanup_local_demo_data.py
```

To inspect a specific accidental local onboarding record as well:

```powershell
python scripts/cleanup_local_demo_data.py --company-id 123
```

## Confirmed cleanup

Run the same command with `--confirm` only after reviewing every printed ID and
count:

```powershell
python scripts/cleanup_local_demo_data.py --company-id 123 --confirm
```

The cleanup is transactional. A foreign-key refusal rolls the operation back;
the script does not weaken constraints or broaden its candidate rules.
