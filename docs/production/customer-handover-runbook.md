# Production customer handover runbook

Use only after the production audit's GO gates are satisfied. Do not use local
demo identities, the development database, Quick Tunnel, or `restore_admin.py`.

## Before onboarding

- [ ] Contract, Privacy Notice/DPA, supported scope, AI/accounting disclaimer,
      subprocessors, support, billing, cancellation, retention, and exit terms accepted.
- [ ] Legal company identity, currency, jurisdiction, fiscal year, chart choice,
      subscription term, authorized admin, and support contacts confirmed.
- [ ] Empty production database, migrations, backup, monitoring, and HTTPS verified.
- [ ] Platform owner bootstrapped with the supported CLI, password changed, and MFA
      enabled when implemented. No demo/test users or companies exist.

## Onboard and hand over

1. The platform owner uses Client Onboarding; never create tenant rows with SQL.
2. Select standard, blank, or optional Yemen starter chart explicitly. Do not add demo journals.
3. Confirm the client admin belongs only to that company and a subscription row exists.
4. Record the HTTPS login URL and admin email. The temporary password is shown once.
5. Send URL/email and temporary password through approved separate channels where possible.
6. Never place passwords in logs, tickets, analytics, audit descriptions, or lasting documents.
7. Client logs in, changes the temporary password immediately, and confirms the old
   token/session is invalid. Enroll MFA when the production design supports it.
8. Client verifies company, users/roles, fiscal periods, opening balances/chart,
   journals, all reports, exports, subscription details, language/RTL, and mobile access.
9. Record acceptance, signatories, date, release, migration, and support route without secrets.

## Break-glass and offboarding

Keep at least two controlled platform owners once operations begin. Never deactivate
the final active superuser. Use the bootstrap CLI's explicit `--promote` path only
after identity verification and incident approval. On termination, follow the
approved export, retention, legal hold, deletion-verification, billing, and credential
revocation policies; repository cleanup scripts are never production offboarding tools.

## Objective handover evidence

Approved contract/privacy artifacts, onboarding audit event, forced-password-change
audit event, subscription record, tenant isolation test, accountant-approved opening
state/report reconciliation, backup coverage, named support contacts, and signed acceptance.
