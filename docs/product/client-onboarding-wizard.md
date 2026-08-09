# Client Onboarding Wizard

How the platform operator turns a signed agreement into a working tenant: one
page, one request, one message to send the client.

## Why it exists

Before this feature, handing over a new client meant three unrelated screens and
a gap the product could not close:

1. Create the company — but `POST /companies` makes its *caller* an admin member,
   so the platform operator ended up inside the client's user list.
2. Create the client's first user — there was no way to do this except by
   inviting them, which needs an email the system cannot send.
3. Set the subscription term — a fourth trip, to a different page.

Nothing tied the three together, so a failure halfway left a half-built tenant
behind, and the operator still had to compose the credentials message by hand.

The wizard drives a single endpoint that does all of it in one transaction.

## Who can use it

**Platform owners only** (`users.is_superuser = true`). The route is registered
in `PLATFORM_PAGES`, so `ProtectedRoute` gates it on the platform flag rather
than on `canViewPage`, which lets unknown paths through by default. A company
administrator — the strongest tenant role there is — who navigates to
`/platform/onboarding` directly gets an **Access Denied** panel inside the app
shell, before any request is made.

The backend gate is `get_current_platform_admin`, the same dependency the
subscriptions page uses. It authorises on `is_superuser` alone; company
membership is never consulted, because the company being created does not exist
yet.

## The five steps

Route `/platform/onboarding`, under **Platform → Onboard Client** in the sidebar.

| Step | Collects |
| --- | --- |
| 1. Client company | Company name (must be unique), base currency |
| 2. Client admin | Admin email, full name, and how the password is set |
| 3. Subscription | Plan code, `active` or `trial`, expiry date, quick terms |
| 4. Accounting setup | Seed chart of accounts, create fiscal year, open periods |
| 5. Review and create | Everything above, then one button |

Steps can be revisited by clicking a completed step in the header; jumping ahead
is not possible. Every step is validated on leaving it, and the whole form is
re-validated on submit — an operator can walk back and empty a field that was
valid the first time through.

### Step 2: three ways to set the password

| Mode | What happens |
| --- | --- |
| **Generate a password** (default) | The server generates a 16-character password that satisfies the account policy and returns it once |
| **Set a password** | The operator types one; the wizard applies the same rule the backend does before sending |
| **Reuse an existing account** | An account that already exists on the platform is attached to the new company and keeps its own password |

The first two modes hand a credential to a human being, so the new account is
created with `must_change_password = true` and reaches nothing but the change
screen until it picks its own. The third does not, so it is left alone. See
[secure-client-handover.md](secure-client-handover.md).

Generation happens on the server (`app/application/onboarding/passwords.py`)
using `secrets.SystemRandom`, over an alphabet with the ambiguous glyphs
(`l`, `I`, `O`, `0`, `1`) removed so the password survives being read aloud.

### Step 3: how the term is sent

An `active` subscription sends its date on `subscription_expires_at`. A `trial`
sends it on `trial_ends_at`, and the backend copies that into `expires_at` —
without this, a trial would never lapse, because the effective-status rule only
inspects `expires_at`.

Quick terms fill the date field with +1 month, +3 months or +1 year. A bare
calendar day is converted to `23:59:59Z` of that day, matching the subscriptions
page, so "expires 31 December" means the client works through the 31st. Days
remaining is shown live, and a date already in the past is called out before
submit — the backend refuses it with 422 regardless.

### Step 4: what gets created

The chart is a three-way choice; the two calendar toggles default to on. All are
idempotent:

- **Chart of accounts** — one of three starting points:

  | Choice | Result |
  | --- | --- |
  | Standard chart *(default)* | The same `DEFAULT_ACCOUNTS` list as `POST /accounts/seed-defaults` |
  | Blank chart | No accounts at all; the client builds the chart themselves |
  | Regional starter | An opt-in template, e.g. `yemen_cash_wallet` |

  Existing codes are skipped, never duplicated. A regional template is never the
  default, and its payment accounts are ordinary editable accounts — see
  [Custom Chart of Accounts](custom-chart-of-accounts.md).

- **Fiscal year** — the current calendar year, 1 January to 31 December, `open`.
  Skipped if a year already covers today.
- **Monthly periods** — twelve `open` periods inside that year. Each is guarded
  by a lookup for the month it would cover, so re-running creates nothing.

Opening periods requires the fiscal year; unchecking the year disables and
clears the periods toggle.

No journal entries are created. A new tenant starts with a chart of accounts and
an open calendar, and nothing in its books.

## Atomicity

The whole onboarding is one transaction. Repositories flush; the route owns the
single `db.commit()`. Every refusal the use case can raise is raised *before the
first write*, and the route calls `db.rollback()` on any `OnboardingError`.

A client is therefore either fully set up — company, admin, membership,
subscription, accounts, calendar, audit row — or not created at all. There is no
state in which a company exists without its admin, or an admin without a
subscription.

## Isolation guarantees

These are the properties the tests exist to defend:

- **The platform owner does not become a member.** Exactly one `company_users`
  row is written by the onboarding, and it belongs to the client's admin. The
  operator never appears in the new company's user list.
- **The client admin is scoped to one company.** It is created with
  `is_superuser = false` and a single `admin` membership. `GET /companies`
  returns that company and nothing else.
- **Reusing a platform admin is refused.** Attaching an `is_superuser` account
  as a client admin would put the operator inside a tenant, so it is rejected
  with 409 rather than silently allowed.
- **A refused onboarding leaves nothing behind.** After a duplicate-name refusal
  the company count is unchanged.

## Credential handling

The plaintext password exists in exactly two places: a local variable in the
route, and the response body of the request that created the account.

- It is **hashed** on the way into the database, like any other password.
- It is **never written to the audit log.** The `new_values` dictionary is
  enumerated field by field and has no password key.
- It is **returned once**, on the 201 response. There is no endpoint that can
  read it back.
- The wizard **drops it from state** when the operator starts another
  onboarding, so it cannot leak into the next client's session.
- Reusing an existing account returns `generated_password: null` — that account
  keeps its own credentials and there is nothing to hand over.
- It is **spent on first use.** The account it belongs to is created with
  `must_change_password = true` and is refused everywhere except `/auth/me` and
  the change endpoint until it is replaced.

The success screen says so plainly, in both languages, before the operator
navigates away.

## The handover message

The success screen renders a ready-to-send message with a copy button:

```
Hello,

Your accounting system access has been created.

Login URL: https://accounting.example.com
Company: Northwind Trading
Admin email: admin@northwind.test
Temporary password: Sw1ftPelican42
Subscription valid until: 2026-09-30

This password is temporary. The system will ask you to set a new one the first
time you log in, and nothing else opens until you do. You can then invite your
team members from Company Users.
```

In Arabic:

```
مرحبًا،

تم إنشاء حساب شركتكم في نظام المحاسبة.

رابط الدخول: https://accounting.example.com
الشركة: Northwind Trading
البريد الإداري: admin@northwind.test
كلمة المرور المؤقتة: Sw1ftPelican42
الاشتراك صالح حتى: 2026-09-30

كلمة المرور هذه مؤقتة، وسيطلب منكم النظام تعيين كلمة مرور جديدة عند أول تسجيل
دخول، ولن يفتح أي شيء آخر قبل ذلك. بعد ذلك يمكنكم إضافة أعضاء فريقكم من صفحة
مستخدمي الشركة.
```

The login URL comes from `APP_PUBLIC_URL`. When it is unset the server sends
`[add your domain here]` instead, and the success screen raises a warning
callout on it — a wrong guessed domain in a message the operator forwards is
worse than an obvious blank. See
[secure-client-handover.md](secure-client-handover.md).

The message is built in two places on purpose:

- `app/application/onboarding/handover.py` produces the English text, so API and
  CLI callers get something usable without a translation table. It is returned
  on `handover_message`.
- `frontend/src/features/onboarding/handoverMessage.ts` rebuilds it in the
  operator's language. The English output matches the backend line for line,
  which a test asserts.

When an existing account is reused, the password line is dropped and the closing
instruction becomes "Please log in with your existing password."

## API

Both routes require `get_current_platform_admin`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/platform/onboarding/defaults` | Currencies, plan codes, expiry presets, `public_login_url`, generated-password length |
| `POST` | `/platform/onboarding/clients` | Create the tenant (201) |

The 201 response carries `generated_password` (once), `must_change_password`,
`public_login_url` and the rendered `handover_message`.

### Request

```json
{
  "company_name": "Northwind Trading",
  "base_currency": "USD",
  "admin_email": "admin@northwind.test",
  "admin_full_name": "Dana Reyes",
  "generate_password": true,
  "temporary_password": null,
  "reuse_existing_user": false,
  "plan_code": "monthly",
  "subscription_status": "active",
  "subscription_expires_at": "2026-09-30T23:59:59Z",
  "trial_ends_at": null,
  "seed_default_accounts": true,
  "chart_template": "default",
  "create_fiscal_year": true,
  "open_monthly_periods": true,
  "onboarding_note": "Signed 12-month agreement"
}
```

`subscription_expires_at` is required unless `trial_ends_at` is given. Exactly
one of `generate_password`, `temporary_password` or `reuse_existing_user` must
be chosen.

### Refusals

| Condition | Status |
| --- | --- |
| Company name already taken | 409 |
| Admin email already has an account, without `reuse_existing_user` | 409 |
| Reused account is a platform admin | 409 |
| Reused account is deactivated | 409 |
| No account exists and no password was supplied | 422 |
| Subscription window is already expired | 422 |
| Password fails the account policy | 422 |
| Caller is not a platform admin | 403 |

The wizard maps each of these to a specific sentence in both languages; nothing
falls through to a raw backend string.

## Audit trail

One row per onboarding:

- `action`: `onboard_client`
- `entity_type`: `client_onboarding`
- `entity_id`: the new company ID
- `company_id`: the new company ID
- `new_values`: company name, currency, admin email and user ID, whether the
  account was reused, plan code, subscription status, expiry, seeded account
  count, fiscal year and period counts, and the operator's note
- `actor`: the platform administrator's email (or `cli` for the script)

No password field appears anywhere in the row.

## Command-line helper

`backend/scripts/onboard_client.py` mirrors the wizard for terminal use — the
page is the primary tool, this exists for the very first client, handed over
before anyone has a platform login, and for support sessions over SSH.

```
python scripts/onboard_client.py --company-name "Acme Trading" \
    --admin-email admin@acme.com --expires 2027-01-31

python scripts/onboard_client.py --company-name "Acme Trading" \
    --admin-email admin@acme.com --trial-ends 2026-09-30 --status trial

python scripts/onboard_client.py --company-name "Acme Trading" \
    --admin-email admin@acme.com --expires 2027-01-31 \
    --password "Str0ngHandover" --no-fiscal-year
```

It generates a password when none is supplied, prints the English handover
message once, and writes the same audit row the API does. The password reaches
the terminal and nowhere else — do not pipe the output into a file that outlives
the handover. It prints the `APP_PUBLIC_URL` login address and warns when that
variable is unset, since the message is not worth sending without it.

## Limitations

Deliberately out of scope, and worth knowing before you rely on them:

- **No email is sent.** The system has no mail transport. The operator delivers
  the handover message through whatever channel it already uses with the client.
- **No payment gateway and no invoices.** The subscription records a commercial
  outcome; it does not collect money. See
  [saas-subscription-model.md](saas-subscription-model.md).
- **No self-service signup.** A client cannot create its own company. Every
  tenant is created by the platform operator.
- **No demo journal entries.** The wizard seeds structure, not bookkeeping. Use
  `backend/scripts/seed_demo_data.py` when a populated tenant is wanted.
- **The login URL has to be configured.** The system cannot infer its public
  address. Until `APP_PUBLIC_URL` is set the message carries a visible
  placeholder.
- **Temporary passwords do not expire.** The first login is forced through a
  password change, but a handed-over password that is never used stays usable
  indefinitely.
- **Company names are compared case-insensitively but are not unique in the
  database.** The 409 is enforced by a lookup in the use case, not by a
  constraint, so a company created outside this endpoint can still collide.

## Tests

- `backend/tests/test_client_onboarding.py` — 29 HTTP integration tests covering
  authorisation, refusals, atomicity, isolation, credential handling, the forced
  password change on the new admin, the seeded chart of accounts and fiscal
  calendar, and the trial window.
- `backend/tests/test_onboard_client_script.py` — 12 tests for the CLI.
- `frontend/src/test/smoke/ClientOnboardingRouteGuard.test.tsx` — the platform
  route guard.
- `frontend/src/test/smoke/ClientOnboardingWizard.test.tsx` — step validation,
  the request payload for active and trial terms, the success screen, the public
  login URL and the first-login notice, password clearing, and each mapped error.
- `frontend/src/test/smoke/handoverMessage.test.ts` — the English message line
  for line, the Arabic message, the server-sent URL, and the reused-account
  variant.

The forced password change itself is covered separately; see
[secure-client-handover.md](secure-client-handover.md).
