# Baseline Run — 2026-07-29

## Purpose

This directory records the Phase 0 reference run before Clean Architecture refactoring.

## Git baseline

- Branch: main
- Last commit captured in: 02-last-commit.txt
- Git status captured in: 01-git-status.txt

## Backend test baseline

Command output file:

- 04-backend-pytest.txt

Result:

- 606 passed
- 3 skipped
- Duration: 159.88s

## Alembic baseline

Command output files:

- 05-alembic-current.txt
- 06-alembic-heads.txt

Result:

- Current revision: a6f4c2d8e1b7 (head)
- Head revision: a6f4c2d8e1b7 (head)

Note:

PowerShell reported NativeCommandError while capturing Alembic informational output, but Alembic still reported the expected current/head revision.

## Frontend lint baseline

Command output file:

- 08-frontend-lint.txt

Result:

- 0 errors
- 2 warnings

Warnings are the known existing Fast Refresh warnings in:

- frontend/src/auth/AuthContext.tsx
- frontend/src/i18n/index.tsx

## Frontend build baseline

Initial command output file:

- 07-frontend-build.txt

Result:

- Failed due to Windows EPERM file lock while deleting frontend/dist-check assets.
- This is an environment/file-lock issue, not a TypeScript or Vite source error.

Workaround command output file:

- 07b-frontend-build-unique-outdir.txt

Result:

- Build succeeded using unique outDir: frontend/dist-baseline-20260729
- Duration: 8.32s

## Manual verification

Manual browser verification was not recorded in this run.

Recommended URLs for manual checks:

- http://127.0.0.1:8010/docs
- http://localhost:5173

## Summary

This baseline confirms that, before Clean Architecture refactoring:

- Backend tests pass.
- Alembic is at the expected head.
- Frontend lint passes with only known warnings.
- Frontend production build succeeds when avoiding the locked Windows output directory.
