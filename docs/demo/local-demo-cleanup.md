# Local demo data cleanup

Use this workflow only for a local development database that has accumulated
automated-test companies and users. It is not part of application startup and
never runs automatically.

## Safety model

- `APP_ENV` must be exactly `development`; production, staging, and test are refused.
- The default is a dry run. It prints candidate counts, dependent-row counts,
  and a short first/last sample without changing the database.
- Deletion requires the explicit `--confirm` flag.
- Confirmed cleanup commits in restart-safe batches and prints progress after
  every commit. The default batch size is 100 candidates.
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

Run with `--confirm` only after reviewing the dry-run counts and sample:

```powershell
python scripts/cleanup_local_demo_data.py --confirm
```

Choose a different number of candidates per transaction when needed:

```powershell
python scripts/cleanup_local_demo_data.py --confirm --batch-size 250
```

Use `--verbose` to print every company and user identifier. Without it, confirm
mode prints batch progress rather than thousands of individual rows:

```powershell
python scripts/cleanup_local_demo_data.py --confirm --batch-size 100 --verbose
```

Each completed batch is committed before the next starts. Progress includes the
batch number, rows deleted in that batch, cumulative deleted count, and remaining
candidate count. If the command is interrupted, run the dry run again and then
repeat the confirmed command. Already committed rows no longer match the next
plan, so cleanup continues with the remaining candidates.

A failure rolls back only the current batch. The script does not weaken database
constraints or broaden its candidate rules.
