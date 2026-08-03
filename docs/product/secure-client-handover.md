# Secure Client Handover

What happens between "the agreement is signed" and "the client is working in
their own books" — the address they are sent to, the password they are given,
and the door that stays shut until they replace it.

## The problem

Onboarding creates an account and hands its password to a human being over
chat, email or a phone call. From that moment the credential is known to at
least two people, and the system has no way to tell which of them is logging in.
The handover message said *please change your password*; nothing made it happen.

Two things were missing, and they only work together:

1. **An address to send.** The backend cannot infer the domain it is served
   behind, so the message carried a literal `[add your domain here]` that the
   operator had to remember to replace by hand.
2. **A door.** A handed-over password worked indefinitely. An operator who
   onboarded ten clients had ten live passwords sitting in ten chat histories.

## APP_PUBLIC_URL

The public address of the frontend, declared once by the operator:

```
APP_PUBLIC_URL=https://accounting.example.com
```

It is a plain environment variable read through `Settings`, and every caller
reaches it through `app/core/public_url.py` rather than reading the setting
directly.

| Function | Returns |
| --- | --- |
| `public_login_url()` | The configured URL without its trailing slash, or `[add your domain here]` when unset |
| `is_public_url_configured()` | Whether a real value was supplied |

**Why the backend does not infer it.** A request's `Host` header is
attacker-controlled and a reverse proxy may rewrite it, so a URL derived from
the request could be poisoned into a phishing address that the system would then
print in a message the operator forwards to a client. Declaring it once is the
only trustworthy source.

**Why the fallback is a visible placeholder and not `localhost`.** A localhost
URL looks correct in a code review and is useless to a client, so it would ship
quietly. `[add your domain here]` cannot be mistaken for a working address —
the wizard raises a warning callout on it and the CLI prints a warning line.

Set it to whatever the client actually opens:

| Environment | Value |
| --- | --- |
| Production | `https://accounting.example.com` |
| Production | `https://app.city-technology.com` |
| Local only | `http://localhost:5173` |

Trailing slashes and surrounding whitespace are stripped before anyone reads
the value, so `https://example.com/` and `https://example.com` behave alike.

It is consumed in four places: the backend handover message, the CLI output,
the `public_login_url` field on both onboarding API responses, and the frontend
handover message, which renders the value the server sent rather than deciding
for itself.

## Temporary password lifecycle

`users.must_change_password` is a single boolean, `NOT NULL DEFAULT false`,
added by migration `b2e5c8f14a37`. Existing accounts backfill to `false` —
none of them is holding a credential anybody handed over.

| Event | Flag |
| --- | --- |
| Normal registration | `false` |
| Demo seed user | `false` |
| Onboarding creates a new admin (generated **or** operator-supplied password) | **`true`** |
| Onboarding reuses an existing account | `false` |
| The account completes the change | `false`, permanently |

The reuse case is the one worth stating explicitly: that account keeps a
password only its owner knows, nothing was handed over, and forcing a change
would be a lockout with no security benefit.

The plaintext never touches the database, the audit log or any log line. It
exists in one local variable in the route and in the body of the single 201
response that created the account.

## The forced change

### What it blocks

The gate hangs off `get_current_user`, not off individual routers, so it is
**deny-by-default**: any endpoint that authenticates a user is covered the
moment it is written. A route that forgets to opt in is blocked, not open.

Reachable while the flag is set:

| Endpoint | Why |
| --- | --- |
| `POST /auth/login` | Never reaches the dependency; also reports the flag |
| `POST /auth/register` | Never reaches the dependency |
| `GET /auth/me` | The screen has to know who it is talking to |
| `POST /auth/change-temporary-password` | The way out |

Logout is client-side — the token is discarded — so it needs no exemption.

Everything else is refused: company business endpoints, accounting, reports, AI
and assistant endpoints, company management, company users, platform
subscriptions, and platform onboarding.

**No role is exempt.** A company administrator is the strongest tenant role
there is, and the platform owner is the only account that could plausibly be
excused; both are refused, and both have a test that says so. An operator who
sets up their own account through onboarding is holding the same kind of
credential as anybody else.

### The refusal

```
HTTP 403 Forbidden

{
  "detail": {
    "code": "PASSWORD_CHANGE_REQUIRED",
    "message": "You must change your temporary password before using the system."
  }
}
```

The shape mirrors `SUBSCRIPTION_INACTIVE`, so a client that already
discriminates on `detail.code` needs no new parsing.

### The endpoint

```
POST /auth/change-temporary-password
Authorization: Bearer <token>

{
  "current_password": "Sw1ftPelican42",
  "new_password": "Ch0senByTheClient",
  "confirm_password": "Ch0senByTheClient"
}
```

Returns the updated `UserRead`, with `must_change_password` now `false`.

| Condition | Status |
| --- | --- |
| Current password is wrong | 400 |
| New password fails the account policy (8+, upper, lower, digit) | 422 |
| Confirmation does not match | 422 |
| New password equals the current one | 422 |
| No token | 401 |

It is reachable whether or not the change is forced, so an account that has
already cleared the flag uses the same door for a routine rotation. There is no
second endpoint to keep in step.

One audit row is written per change: `action = change_password`,
`entity_type = user`, `entity_id` the user. Neither the old nor the new
password appears in `description`, `old_values` or `new_values`.

## What the client sees

`must_change_password` is exposed in three places so the frontend never has to
guess:

- the login response (`TokenRead`), so the client routes straight to the change
  screen instead of bouncing off the first business call it tries;
- `GET /auth/me` (`UserRead`), which is what the session is rebuilt from;
- the onboarding response, so the operator can tell the client what to expect.

The screen lives at `/auth/change-temporary-password` and is deliberately
**outside the application shell** — the same focused, auth-style page as login.
The shell's sidebar, company switcher and dashboard widgets all call endpoints
that would be refused, so mounting it would paint a chrome of dead controls
around the one form that works. It carries the theme toggle and a sign-out
button, supports light and dark, English and Arabic with RTL, and is responsive.

Three guards keep the routing honest, and all three read the same flag:

| Guard | Behaviour |
| --- | --- |
| `LoginPage` | Sends a flagged account to the change screen instead of the dashboard |
| `AppLayout` | Redirects out of the shell to the change screen |
| `ProtectedRoute` | Same redirect, for any future route used outside the shell |

The change route itself redirects a user with the flag already cleared to the
dashboard, so nobody can get stuck on a form they have no reason to submit.

On success the page re-reads the session through `refreshUser()` and navigates
to the dashboard. Validation runs locally first — mismatch, reuse and policy —
so a typo costs a sentence rather than a round trip that returns raw JSON. No
backend error string is rendered; every status maps to a translated sentence.

## Platform onboarding

The wizard's success screen now shows:

- **the real login URL** from `public_login_url`, in the summary grid and in the
  handover message;
- **a warning callout** when the server sent the placeholder, because that is
  the one thing an operator must fix before the message is worth sending;
- **the one-time password**, with the warning that it is shown once;
- **the first-login notice**, gated on `must_change_password` rather than on
  whether a password was generated.

The handover message closes with the change requirement in both languages:

> This password is temporary. The system will ask you to set a new one the
> first time you log in, and nothing else opens until you do. You can then
> invite your team members from Company Users.

Reusing an existing account drops the password line and closes with "Please log
in with your existing password" instead. Nothing is forced, because nothing was
handed over.

The plaintext is dropped from wizard state when the operator starts another
onboarding, so it cannot leak into the next client's session.

The CLI (`backend/scripts/onboard_client.py`) prints the same URL, warns when
`APP_PUBLIC_URL` is unset, and states that the password is shown once and must
be changed at first login. It writes the same audit row the API does, without
the password.

## Subscription page density

`/platform/subscriptions` was built as a card-shaped table: eight columns, tall
rows, and six full-width buttons stacked in the last cell, so a list of ten
tenants ran well past the fold and the action column dominated every row.

The logic is untouched. What changed is density:

- Eight columns folded into five. Currency and member count moved under the
  company name; days-remaining moved under the expiry date; the plan kept its
  own column on desktop and folded into the subtext on mobile.
- A `.data-table-compact` modifier tightens row padding. The default is tuned
  for financial statements, where figures need air; an operational list of one
  short line per row does not.
- **All six actions are kept.** Activate (when the subscription is not already
  active), Extend 1 month and Edit stay labelled; Extend 1 year, Suspend and
  Cancel become icon buttons behind a divider, each with a `title` and an
  `aria-label` carrying the same text the labelled buttons use.
- The desktop breakpoint dropped from `xl` to `lg`, so the table appears on
  more screens before the card layout takes over.
- Mobile cards were compacted rather than replaced.

No dropdown component exists in the design system, and introducing a menu
dependency for six buttons would have been a larger change than the polish
warranted, so the secondary actions are a compact grouped set instead.

Search, the status filter, the loading, empty and error states, the
confirmation prompts, RTL and the light/dark palettes are all unchanged.

## Limitations

Worth knowing before relying on any of this:

- **Existing tokens survive the change.** Access tokens are stateless JWTs and
  the system keeps no revocation list, so a token minted before the password
  change stays valid until it expires. Nothing to revoke means nothing is
  revoked; a session store would be the fix, and is out of scope here.
- **No email is sent.** The system has no mail transport. The operator delivers
  the handover message through whatever channel it already uses with the client.
- **No self-service password reset.** A client who forgets their password needs
  the operator. There is no "forgot password" email flow.
- **Temporary passwords do not expire.** The flag forces a change at first
  login, but a handed-over password that is never used stays usable
  indefinitely. There is no window after which onboarding credentials lapse.
- **Accepting a company invitation is not gated.** `POST
  /company-users/invitations/accept` authenticates through
  `get_current_user_optional`, which the gate does not cover. Accepting an
  invitation grants no data access on its own — the next request is refused like
  any other — so this is a known gap rather than a hole.
- **`APP_PUBLIC_URL` is not validated as a URL.** It is trimmed of whitespace
  and trailing slashes and otherwise printed as given. A typo reaches the client.
- **No domain is deployed yet.** Until the system is hosted, the only honest
  value is `http://localhost:5173`, which is useful for a local demo and useless
  in a real handover. Leaving it empty is the safer default.

## Tests

Backend:

- `backend/tests/test_forced_password_change.py` — 15 HTTP integration tests:
  the flag on login and `/auth/me`, business and company endpoints refused with
  the structured 403, a flagged platform admin refused on both platform
  surfaces, the current-password check, the policy check, mismatch and reuse
  refusals, the flag clearing and the hash being replaced, the business API
  opening afterwards, the audit row carrying neither password, and a settled
  account rotating its own credential through the same endpoint.
- `backend/tests/test_public_url.py` — normalisation, the placeholder fallback,
  and the handover message carrying the configured URL rather than a guess.
- `backend/tests/test_client_onboarding.py` — the new admin is flagged, a reused
  account is not, and the handover message carries `public_login_url`.
- `backend/tests/test_onboard_client_script.py` — the CLI prints the configured
  URL, warns when it is unset, and its admin is locked out until the change.

Frontend:

- `frontend/src/test/smoke/ChangeTemporaryPassword.test.tsx` — the English and
  Arabic copy, the submit-refresh-redirect path, local mismatch and policy
  refusals that never reach the API, and a wrong current password explained as a
  sentence rather than as response JSON.
- `frontend/src/test/smoke/PlatformRouteGuard.test.tsx` — a flagged platform
  admin is sent to the change screen rather than shown the page or an access
  refusal.
- `frontend/src/test/smoke/PlatformSubscriptionsPage.test.tsx` — the status
  badge and all six actions survive the density pass, and Activate stays hidden
  on an already-active subscription.
- `frontend/src/test/smoke/ClientOnboardingWizard.test.tsx` — the success screen
  shows the public URL and the first-login notice, and warns when the server
  sent the placeholder.
- `frontend/src/test/smoke/handoverMessage.test.ts` — the message carries the
  server's URL verbatim, including the placeholder.
