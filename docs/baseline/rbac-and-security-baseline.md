# RBAC and Security Baseline

## Authentication and JWT

- Authentication uses bearer JWTs created and decoded through
  `backend/app/core/security.py`.
- Access-token expiry is configuration-driven.
- Protected dependencies reject absent, invalid, or malformed tokens.
- Current-user resolution loads the user and rejects inactive accounts.
- A token issued before global deactivation must no longer authorize the now
  inactive user.
- Authentication errors must retain current status and detail behavior.

Evidence: `auth_dependencies.py`, `security.py`,
`test_rbac_permission_matrix.py`, and all `test_protected_*.py` modules.

## Protected resources

Accounts, companies, fiscal records, journal entries, reports, audit logs,
company users, assistant conversations, and AI accounting operations enforce
their current authentication requirements. A route extraction must not make an
existing protected dependency optional.

## Company access

`backend/app/core/company_access.py` currently resolves company context from:

- An active user.
- Active company membership for ordinary users.
- Explicit superuser handling with company context.

Baseline expectations:

- Inactive users cannot access a company, including inactive superusers.
- Ordinary users cannot access a company without an active membership.
- Company operations remain isolated to the selected company.
- Cross-company account, journal, user, invitation, report, and audit data is not
  revealed.
- Role resolution remains deterministic and does not mutate state.

Evidence: `test_rbac_permission_matrix.py`,
`test_protected_company_users.py`, protected resource tests, and
`test_global_user_admin_authorization.py`.

## Company roles

Current role distinctions include administrative and non-mutating roles such as
viewer, with explicit permission mappings. Company administrators can manage
company-scoped access subject to safeguards; viewers cannot perform
administrative mutations.

Future use-case extraction must preserve:

- Page/action permission distinctions.
- Company-scoped administrator behavior.
- Last-active-admin protections.
- Non-mutating role restrictions.
- Current not-found versus forbidden behavior where it prevents information
  disclosure.

Evidence: `test_rbac_permission_matrix.py` and
`test_protected_company_users.py`.

## Platform superusers and global account status

Global account activation/deactivation is distinct from company membership:

- Only a platform superuser may globally deactivate or reactivate users.
- A company administrator may manage authorized company access but may not
  change global account status, even for a user in the same company.
- Global deactivation changes the user account, not unrelated company
  memberships.
- Removing/restoring company access changes only the selected membership.
- A superuser cannot deactivate their own account.
- The final active superuser cannot be deactivated.
- Global status changes and their audit records are atomic.

Evidence: `test_global_user_admin_authorization.py`,
`test_protected_company_users.py`, and
`test_rbac_permission_matrix.py`.

## Invitation lifecycle

Baseline invitation behavior:

- Email comparison uses normalized identity semantics.
- A company cannot have duplicate live invitations for the same normalized
  email.
- Different companies may invite the same normalized email.
- Reissuing after expiry preserves and supersedes the old row rather than
  destructively rewriting history.
- Expired or cancelled invitations cannot be validated or accepted.
- Acceptance succeeds once and must not duplicate users, memberships, or audit
  records.
- An inactive existing membership requires the explicit restore workflow.
- Invitation registration uses the current password policy.
- Raw invitation tokens and token hashes must not appear in audit logs.
- Create, accept, and cancel operations remain atomic.
- Concurrent create/accept/cancel races retain one valid outcome.

Evidence: `test_invitation_lifecycle_integrity.py` and
`api/test_company_user_invitations.py`.

## Rate limiting and login lockout behavior

`auth_routes.py` uses `core/rate_limit.py` for:

- Registration rate limiting.
- Failed-login rate limiting/temporary lockout behavior.

Configuration includes the failed-login limit, registration limit, and window
durations. Refactoring authentication must retain current keys, attempt-recording
semantics, thresholds, response codes, and reset behavior. The current
implementation appears process-local; replacing it with distributed storage
would be a separate operational change, not incidental architecture work.

## Password and identity safety

- Registration and invitation acceptance use the current password-strength
  policy.
- Email normalization must continue supporting mixed-case or padded legacy
  lookup where currently covered.
- Password hashes, access tokens, invitation tokens, provider keys, and `.env`
  values must never be logged or exposed.

Evidence: `test_password_policy.py`,
`test_invitation_lifecycle_integrity.py`, and email-normalization tests.

## Security invariants for refactoring

Future changes must not weaken:

- Authentication on protected endpoints.
- Token invalidation through active-user lookup.
- Company isolation.
- Explicit role/permission checks.
- Last-admin and final-superuser protections.
- Global versus company-scoped user action separation.
- Invitation token confidentiality and one-time lifecycle.
- Rate limiting.
- AI prompt-injection, data minimization, grounding, and confirmation controls.
