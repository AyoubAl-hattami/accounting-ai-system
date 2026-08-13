# Final production gate

Decision owner: `<pending>`  Release: `<pending>`  Review date: `<pending>`

Every item requires a dated evidence link and named approver. Repository files,
local tests, templates, and verbal confirmation alone do not satisfy external gates.

| Gate | Status | Evidence and approver |
|---|---|---|
| Code validation and security regression suites green | [ ] | `<pending>` |
| Tagged immutable staging deployment completed | [ ] | `<pending>` |
| Real DNS, HTTPS certificate/renewal, redirect, and security headers verified | [ ] | `<pending>` |
| Managed/approved real PostgreSQL, TLS, least privilege, and capacity verified | [ ] | `<pending>` |
| Secret manager injection, access control, rotation, and redaction verified | [ ] | `<pending>` |
| Encrypted backup created and independently verified | [ ] | `<pending>` |
| Isolated restore drill completed within approved RPO/RTO | [ ] | `<pending>` |
| Monitoring dashboards and alert delivery verified | [ ] | `<pending>` |
| Application rollback and database recovery decision path rehearsed | [ ] | `<pending>` |
| Platform owner bootstrap, forced password change, and old-token rejection tested | [ ] | `<pending>` |
| Demo/test users, companies, journals, credentials, and provider keys absent | [ ] | `<pending>` |
| Distributed rate limit and trusted client-IP behavior verified | [ ] | `<pending>` |
| Platform administrator MFA/session-security risk approved | [ ] | `<pending>` |
| Legal, privacy, DPA, subprocessor, AI, and accounting-scope approvals complete | [ ] | `<pending>` |
| Support, incident, billing, retention, export, and exit owners accepted duties | [ ] | `<pending>` |
| Customer handover checklist signed | [ ] | `<pending>` |

## Decision rule

`GO` requires every row complete, no open Severity 1/2 defect, and written approval
from engineering, operations/security, legal/privacy, accounting/product, support,
and the accountable business owner. A conditional exception must be explicit,
time-bounded, owned, customer-disclosed where appropriate, and must not waive a
critical security, restore, legal, or data-integrity control. Until then the decision
remains **NO-GO**.
