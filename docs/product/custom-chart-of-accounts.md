# Custom Chart of Accounts

A company's chart belongs to the company. The system supplies a starting point,
never a structure the client has to live inside.

## The problem

The product shipped one default chart and no way to add an account from the UI.
The Accounts page could seed the defaults and list what it found, and that was
all. A business whose money actually moves through a cash box, a local bank and
two mobile wallets had no way to say so.

That is not an edge case. In Yemen a small business may settle almost everything
through Al Kuraimi, Jawali, One Cash and a physical cash box, and none of those
appear in a generic chart. The same is true of any country the product has not
been tuned for — which is every country.

## What was already true

Worth stating, because it shaped how small the change needed to be:

- Accounts are unique only on `(company_id, code)`. Any code, any name.
- Reports (`trial balance`, `P&L`, `balance sheet`) classify **strictly by
  `account_type`**. No report has ever matched on an account's name.
- A company with zero accounts is valid; the reports simply come back empty.

So the backend never forced a structure. The gap was a missing create form, a
missing way to say what an oddly named account *is*, and a seeder with exactly
one option.

## account_subtype

A nullable, descriptive column on `accounts`:

```
bank | cash | e_wallet | receivable | payable | revenue | expense | other
```

| It does | It does not |
| --- | --- |
| Group accounts for humans on the Accounts page | Appear in any report |
| Help the assistant resolve "from the wallet" | Affect debit/credit rules |
| Get set, changed or cleared at any time | Get required — `NULL` is normal |

**Reports ignore it entirely.** This is the property that makes the column safe:
adding it cannot change a single number, because no report reads it. It is
validated by a check constraint so an unknown value cannot be stored, and it is
deliberately *not* in the protected-field set, so an account seeded before the
column existed can be classified later.

### Why the assistant needs it

An account named `الكريمي` matches no alias in any language list. Before the
subtype, a user saying "paid 300 from the bank" against a chart containing only
`الكريمي` got a clarification question, because nothing connected the two.

`account_mapper.py` now treats the company-declared subtype as an extra matching
signal (`SUBTYPE_ALIAS_CATEGORIES`), so a `bank` hint reaches an account no
alias list could have predicted. Accounts without a subtype score exactly as
they did before, so no existing mapping changed.

The mapper also tries a free-text preference verbatim before falling back, and
`e_wallet` accounts are now a payment source of last resort alongside bank and
cash — a company that holds no bank account and no cash box can still be paid
from.

## Starter templates

`app/application/accounts/defaults.py` holds a registry:

| Code | Contents |
| --- | --- |
| `default` | The generic chart, unchanged (13 accounts) |
| `yemen_cash_wallet` | Cash box, a local bank, two mobile wallets, plus the usual spine (17 accounts) |

`resolve_chart_template(name)` returns the accounts for a code and **falls back
to `default`** for anything unrecognised, including `None`.

Two rules govern any regional template:

1. **It is never the default.** `default` is the default in the schema, in the
   seed endpoint's query parameter, and in the onboarding wizard's initial form
   state. A country is only ever seeded because someone chose it.
2. **Its payment accounts are not system accounts.** The structural parents
   (`Assets`, `Liabilities`, `Revenue`, …) stay `is_system` so reports keep a
   spine. Every account the client actually transacts through is `is_system =
   false`, so it can be renamed, re-coded or deleted on day one.

Adding a template is adding one tuple and one registry entry. Nothing else in
the system needs to know it exists.

## Onboarding

The wizard's accounting step is a three-way choice, not a toggle:

| Choice | Sends |
| --- | --- |
| Standard chart *(default)* | `seed_default_accounts: true`, `chart_template: "default"` |
| Blank chart | `seed_default_accounts: false` |
| Yemen cash & wallet starter | `seed_default_accounts: true`, `chart_template: "yemen_cash_wallet"` |

Blank means blank: the company is created with zero accounts and the client
builds the chart themselves.

## The Accounts page

`Add account` opens a form with a code, a name, a type, an optional subtype, an
optional parent and a description. The name placeholder shows what the field is
actually for — *e.g. Jawali Wallet, Cash Box, Al Kuraimi* — and the type helper
states the thing that matters: **the type drives every report, and bank
accounts, cash boxes and wallets are all Assets.**

### Quick templates

`Add Bank` / `Add Cash Box` / `Add E-Wallet` (`إضافة بنك` / `إضافة صندوق نقدي` /
`إضافة محفظة إلكترونية`) set the account type to `asset`, set the subtype, and
suggest a name.

They are **pure form prefills**. There is no second creation path, no hidden
field and no special handling — the resulting account goes through the same
endpoint as one typed entirely by hand, and every prefilled value can be
overwritten before saving. The helper text under the buttons says so:
*"These only fill in the form below. Edit anything before saving."*
