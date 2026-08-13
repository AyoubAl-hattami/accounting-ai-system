# Staging deployment smoke test

Status: evidence template. Passing repository tests does not prove this checklist.

Use an isolated staging database and synthetic staging identities only. Never use
customer data, a copy of the local development database, or production secrets.
Record the release tag, image digests, Alembic revision, operator, UTC timestamps,
public domain, and links to redacted evidence before starting.

## Automated, non-destructive probes

Run these against the real staging HTTPS origin. Save status codes, relevant
headers, and timestamps without cookies, tokens, or response data.

```powershell
$origin = "https://<staging-domain>"
curl.exe --fail --silent --show-error --head $origin/
curl.exe --fail --silent --show-error $origin/api/health
curl.exe --fail --silent --show-error --head $origin/platform/dashboard
```

- [ ] HTTP redirects to HTTPS and the certificate chain, hostname, and renewal
      configuration are valid.
- [ ] Frontend returns CSP, HSTS, `X-Content-Type-Options`, referrer, and frame
      protection headers.
- [ ] `/api/health` reaches FastAPI through the public `/api` route.
- [ ] Browser network inspection shows no `localhost`, `127.0.0.1`, tunnel, mixed
      content, or cross-environment requests.
- [ ] A direct refresh on `/login`, `/platform/dashboard`, `/accounts`, and a
      report route returns the SPA instead of a proxy 404.
- [ ] Deliberately unauthenticated and unauthorized requests produce expected
      401/403 responses without stack traces or internal exception text.

## Identity and platform workflow

- [ ] Public `POST /api/auth/register` is unavailable in production mode.
- [ ] Platform owner login succeeds and lands on Platform Dashboard.
- [ ] Platform owner cannot browse tenant accounting routes without membership.
- [ ] Onboard one uniquely named synthetic staging tenant with no demo journals.
- [ ] The temporary password appears once, is delivered through the approved
      channel, and is absent from logs and audit descriptions.
- [ ] Client admin can access only password-change endpoints before changing it.
- [ ] Changing the temporary password invalidates the original access token.
- [ ] Client admin lands in the new tenant; company selection cannot expose or
      retain another tenant's data.
- [ ] Trial, active, suspended, and expired effective subscription states match
      the approved matrix. Non-members cannot discover subscription state.
- [ ] Logout removes browser authentication state and protected refresh returns 401.

## Accounting workflow

- [ ] Create a custom asset account under the synthetic tenant.
- [ ] Create a balanced journal draft; an unbalanced entry is rejected.
- [ ] Review and post according to the configured workflow; never auto-post an AI draft.
- [ ] Trial Balance, Profit and Loss, Balance Sheet, General Ledger, and Account
      Ledger load and reconcile against the known staging fixture.
- [ ] Desktop and mobile basics, dark/light mode, English/Arabic, and RTL remain usable.

Do not silently delete the fixture. Mark it as staging test data and remove it only
through an approved staging reset process after evidence is retained.

## Result record

| Field | Evidence |
|---|---|
| Release/tag and image digests | `<pending>` |
| Domain and certificate report | `<pending>` |
| Migration revision | `<pending>` |
| Smoke start/end UTC | `<pending>` |
| Failed checks and defect links | `<pending>` |
| Engineering/operations sign-off | `<pending>` |

A locally passing test suite is not a substitute for this signed staging record.
