# SaaS Subscription Model

How the platform operator sells access to the accounting system, and how the
application enforces it.

## Two kinds of administrator

The word "admin" means two different things in this product, and keeping them
apart is the whole point of this design.

| | Platform administrator | Company administrator |
| --- | --- | --- |
| Represented by | `users.is_superuser = true` | a row in `company_users` with `role = 'admin'` |
| Scope | every tenant | exactly one company |
| Manages | subscriptions, tenant lifecycle | the client's own users, chart of accounts, bookkeeping |
| Member of client companies | **no** | yes |
| Can change a subscription | yes | **no** |

The platform administrator is deliberately *not* a member of the companies it
sells to. It never appears in the client's user list, and it does not need a
membership to administer a subscription — the platform endpoints authorise on
`is_superuser` alone, through `get_current_platform_admin`.

## Onboarding a client

1. The platform operator creates the company.
2. Creating a company materialises its subscription row as `active` with no
   expiry (`company_routes.create_company_endpoint`), so a freshly handed-over
   tenant is never locked out by accident.
3. The operator creates the client's first user with `role = 'admin'` and hands
   over those credentials.
4. From then on the client manages its own users; the operator only touches the
   subscription, from **Platform → Subscriptions**.
5. The operator sets a term — Extend 1 month, Extend 1 year, or an exact expiry
   date — when the commercial agreement says so.

## Statuses

One subscription per company, enforced by
`uq_company_subscriptions_company`. The stored status is one of:

| Status | Meaning | Grants access |
| --- | --- | --- |
| `trial` | evaluating, still within the trial window | yes, until expiry |
| `active` | paid and current | yes, until expiry |
| `past_due` | term elapsed | no |
| `suspended` | switched off by the operator | no |
| `cancelled` | ended by the operator or the client | no |

### Effective status is derived, not stored

There is no cron job that flips `active` to `past_due` overnight. Instead
`app/application/subscriptions/policy.py` computes an **effective status** on
every read:

- `suspended`, `cancelled` and `past_due` are returned unchanged.
- `trial` and `active` with no `expires_at` are unlimited.
- `trial` and `active` whose `expires_at` has passed report `past_due`.

A subscription that lapses between two requests is therefore enforced on the
very next request, and the platform page always shows the truth rather than the
last state a scheduled job happened to write.

`expires_at <= now` counts as expired. The admin page and the CLI both convert a
chosen calendar day to `23:59:59Z` of that day, so "expires 31 December" means
the client works through the 31st.

### Extending

`Extend 1 month` / `Extend 1 year` add to the **current expiry** when it is in
the future, and to **now** when it has already lapsed — so extending a lapsed
tenant grants a full fresh term rather than backdating it. Month arithmetic
clamps to the last valid day of the target month (31 January + 1 month = 28 or
29 February).

Extending does **not** resurrect a `suspended` or `cancelled` subscription. Those
are deliberate decisions and must be lifted explicitly with Activate. Extending
any other status sets it back to `active`.

## Enforcement

`ensure_company_access` is the single authorisation choke point every
company-scoped endpoint already calls, so the subscription gate was added there
rather than to each router. It defaults to on:

```python
ensure_company_access(db, current_user, company_id)                              # gated
ensure_company_access(db, current_user, company_id, require_active_subscription=False)  # exempt
```

When the gate refuses, the response is **HTTP 403** with a structured detail:

```json
{
  "detail": {
    "code": "SUBSCRIPTION_INACTIVE",
    "message": "Company subscription is inactive or expired.",
    "status": "past_due"
  }
}
```

### What is never blocked

- Login, logout, token refresh and `/auth/me` — they are not company-scoped.
- Password changes.
- `GET /companies/{id}` — the shell needs the company profile to explain the
  lockout, and it carries no accounting data.
- `GET /companies/{id}/subscription` — the endpoint that tells a locked-out
  client *why* it is locked out.
- `GET /company-users/me` — the client resolves its own role from this call.
- Every `/platform/subscriptions` route — the operator must be able to fix the
  thing that is broken.

### Ordering matters

The subscription check runs **after** the membership check. A user who is not a
member of a company is refused with "You do not have access to this company"
and learns nothing about that tenant's commercial state.

### No bypass for company admins

A company administrator is a tenant role. It is checked by the same
`ensure_company_access` call and is refused exactly like every other member.
Only `is_superuser` skips the membership lookup, and platform admins are not
subject to the tenant gate because they never operate inside a tenant.

### Companies with no subscription row

A company that predates this feature, or one created outside the API, has no
row in `company_subscriptions`. Such a company is treated as **unmanaged** and
allowed through: blocking it would lock out working tenants on deploy. The row
materialises the first time a platform admin acts on it, and reads never write.

### Invitation acceptance is not gated — by decision

`POST /company-users/invitations/accept` is token-authenticated and does not
call `ensure_company_access`, so it is **not** subscription-gated. This is
intentional: the invitation flow already refuses inactive companies, the token
is single-use and time-limited, and accepting an invitation grants no access to
any accounting data. Once accepted, the new member hits the gate like everyone
else on their first business request. Gating acceptance itself would only turn
a clear "your subscription is inactive" screen into a confusing broken link.

## Data is preserved

Expiry, suspension and cancellation change **access only**. No company data is
ever deleted by this feature:

- Journal entries, accounts, fiscal periods, users, memberships and audit logs
  are untouched.
- The `company_subscriptions` foreign key is `ON DELETE RESTRICT`.
- Reactivating a company restores it exactly as it was.

Every mutation is written to the audit log with `entity_type =
"company_subscription"` and the acting platform administrator.

## The platform page

Route `/platform/subscriptions`, visible in the sidebar only when
`user.is_superuser`. A non-platform-admin who navigates there directly gets an
**Access Denied** panel inside the app shell — the guard runs before any data is
requested, so no company list is fetched or leaked.

Columns: company, base currency, effective status, expiry, days remaining, plan
code, member count. Actions per row: Activate, Extend 1 month, Extend 1 year,
Edit (status / expiry / plan code), Suspend, Cancel. Suspend and Cancel open a
confirmation modal with an optional reason, which is stored in
`suspension_reason` and shown in the audit trail.

Search filters by company name; the status filter matches the *effective*
status, so an `active` row whose term has lapsed is found under `past_due`.

### API

All routes require `get_current_platform_admin`.

| Method | Path |
| --- | --- |
| `GET` | `/platform/subscriptions?search=&status=&skip=&limit=` |
| `GET` | `/platform/subscriptions/{company_id}` |
| `PATCH` | `/platform/subscriptions/{company_id}` |
| `POST` | `/platform/subscriptions/{company_id}/extend` (`period: month\|year`) |
| `POST` | `/platform/subscriptions/{company_id}/activate` |
| `POST` | `/platform/subscriptions/{company_id}/suspend` |
| `POST` | `/platform/subscriptions/{company_id}/cancel` |

Plus one company-facing read: `GET /companies/{company_id}/subscription`.

## What the client sees when locked out

The app shell stays on screen — sidebar, company selector, language and theme
toggles, sign out. The content area is replaced by a panel showing the current
status badge, the expiry date, and:

> Your company subscription is inactive or expired. Please contact your platform
> administrator.

In Arabic:

> اشتراك شركتك غير نشط أو منتهي. يرجى التواصل مع مسؤول المنصة.

No raw backend error is shown, and no request storm is fired at endpoints that
would only answer 403.

## Command-line helper

`backend/scripts/manage_company_subscription.py` mirrors the page for terminal
use — the platform page is the primary tool, this exists so the operator is
never locked out of its own control plane.

```
python scripts/manage_company_subscription.py list --search acme
python scripts/manage_company_subscription.py show --company-id 3
python scripts/manage_company_subscription.py activate --company-id 3
python scripts/manage_company_subscription.py extend --company-id 3 --years 1
python scripts/manage_company_subscription.py set-expiry --company-id 3 --date 2026-12-31
python scripts/manage_company_subscription.py suspend --company-id 3 --reason "non-payment"
```

## Limitations

This is subscription *access control*, not billing. Deliberately out of scope:

- **No payment gateway.** Nothing charges a card. The operator records the
  commercial outcome by hand.
- **No invoices or receipts.** No invoice numbering, tax lines or PDF billing
  documents.
- **No email notifications.** Nobody is warned that a term is about to lapse;
  the operator watches the days-remaining column.
- **No self-service billing portal.** Clients cannot buy, upgrade or renew on
  their own — every change goes through the platform operator.
- **No plan enforcement.** `plan_code` is a free-text label. It does not cap
  users, entries or features.
- **No proration or partial terms.** Extensions are whole months and years.
- **No subscription history.** One row per company holds the current state; the
  audit log is the record of how it got there.
