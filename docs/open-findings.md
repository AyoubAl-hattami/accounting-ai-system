# Open findings

Findings that have been measured and not yet fixed.

Fixed findings are not listed here: their record is the commit that closed
them, which carries the ID in its subject (`[RAG-1]`, `[D2]`, `[A9]`, and so
on). `closed-findings.md` indexes those by ID, and is also where a finding
that was withdrawn or downgraded lives -- those have no closing commit to
carry them. This file exists for the other kind -- the ones found while
looking for something else, which otherwise survive only in a conversation.

Note that the **F-001 to F-025** index in
`audit-report/Accounting_AI_System_Technical_Audit.md` is a separate
numbering from the IDs used here, and no cross-walk between the two exists.
`F2` here is the process-local rate limiter; `F-002` there is audit
atomicity. They collide by accident. An `F-00x` that looks accounted for here
has not been looked at under that number. See also the caveat at the top of
`closed-findings.md` before matching an ID.

An entry earns its place by being **measured**. Each one states what was run
and what came back, so the next person can reproduce it before deciding
whether it matters. An entry with a plausible story and no measurement is a
guess and does not belong here.

## How this file is ordered

It is the concatenation of two files that were written on two branches and
merged without either superseding the other:

1. **The RAG series** (below) -- full write-ups, each carrying its own
   measurement. From `phase-61-subledger-and-agent`.
2. **Parts 1 to 3** (further down) -- the backlog carried forward from the
   audits, as a table per area with an explicit basis column. From
   `batch-1-deploy-correctness`.

They use different conventions on purpose and both are kept as written. The
second half's **MEASURED / READING-ONLY / ID ONLY** vocabulary is defined in
"How to read the basis column", immediately before it.

---

## RAG-13 · The assistant offers a viewer an action the backend refuses

**Severity** Medium · **Measured** 2026-09-23, branch
`phase-61-subledger-and-agent` at `41143a7`

A journal draft prepared through the conversation-aware retry carries no
`_CAN_CREATE_DRAFT` check. A viewer is shown a draft and a confirm button;
pressing it is refused.

Over HTTP, company A, message `"from the bank"` with the amount in the
preceding turn (`"paid 300 electricity"` / `"bank or cash?"`):

| role | `POST /ai/gemini-assistant` | then `POST /ai/gemini-assistant/confirm-action` |
|---|---|---|
| viewer | 200, `intent=create_journal_draft`, `suggested_action=create_journal_entry_draft` | **403** "You do not have permission to perform this action" |
| accountant | 200, same draft | 200, draft `AI-20260923092219` created |

The shape is [A9]'s: the interface offers something the backend will not do.
Nothing is written -- `/confirm-action` re-validates the role, which is why
this is Medium and not High -- but the viewer is invited to try.

**Why the obvious gate is not the whole answer.** Most routes into a draft
ARE gated: a message with an amount in it is reclassified to `action_request`
and refused by that entry's permission set, which is how
`"it was 300 from the bank"` gets an access_denied for a viewer. The gap is
the narrow path where the amount came from the conversation and the message
carries only the source, so the reclassification does not fire and the retry
runs unguarded. A fix is one permission check in
`_handle_unknown_question`'s first stage; what needs deciding first is
whether a viewer should see the draft at all, or a refusal that explains the
role.

**Where** `gemini_assistant_service._handle_unknown_question`, stage 1.

---

## RAG-14 · "Who are the active users?" is answered from the audit log

**Severity** Low · **Measured** 2026-09-23, same branch and commit

`_classify_intent` routes on the interrogative before the subject, so a
question about users that starts with "who" becomes an audit question.

| message | classified | answered by |
|---|---|---|
| `Who are the active users?` | `audit_question` | recent audit activity |
| `who has access to this company?` | `audit_question` | recent audit activity |
| `من هم المستخدمون النشطون؟` | `audit_question` | recent audit activity |
| `list the users` | `user_question` | the user list |
| `show me company users` | `user_question` | the user list |

Both phrasings of the same question are in the wild; only one of them works.

It has a second effect worth stating: the two intents have different gates
(`_CAN_READ_AUDIT_LOGS` = admin, auditor; `_CAN_READ_USERS` = admin,
auditor). They are equal today, so nothing is over-exposed -- but an
accountant asking about users is refused as if they had asked about audit
logs, and if either set ever moves, the misclassification becomes a
permissions question rather than a phrasing one.

**Where** `gemini_assistant_service._classify_intent`.

---

## RAG-16 · The "Open report" button ignores the period the card shows

**Severity** Low · **Measured** 2026-09-24, same branch

Every grounding card carries a button that navigates to the report page,
with the card's filters in the query string -- `?as_of_date=2026-01-31`,
`?start_date=...&end_date=...`. None of the report pages read them:
`BalanceSheetPage`, `TrialBalancePage`, `GeneralLedgerPage` and
`AccountLedgerPage` contain no `useSearchParams` and no `URLSearchParams`.

So a card that says "As of 2026-01-31" opens a page showing today. The
figures in the card are right and the page is right; they are answers to
different questions, one click apart.

This predates the four new cards -- the profit-and-loss card has built those
parameters since 2026-07-14 and the page has never read them. The new cards
follow the same idiom deliberately rather than inventing a second one; the
fix belongs in the pages, or in a decision that the button is "open the
report" and the period is not carried.

**Where** `frontend/src/features/ai/GroundingCards.tsx` (builds them),
`frontend/src/features/reports/*` (ignore them).


---

## RAG-17 · The aging and partner-statement tests have never run

**Severity** Medium · **Measured** 2026-09-24, branch
`phase-61-subledger-and-agent` at `fca5246`

**Read this as a coverage finding, not a test-health one.** The aging and
partner-statement feature has never been exercised by a passing test --
not once, at any commit. This is not a flaky file, not a file that broke
last week, and not 25 tests that need re-running. It is a feature that
ships with the appearance of a test suite and the coverage of none, and the
appearance is the dangerous part: the file is 25 well-named tests that a
reviewer scanning the tree would count as the aging feature being covered.

`tests/test_aging_and_statements.py` contains 25 tests. All 25 fail, and
have failed at every commit on this branch since the file arrived in
`c6ba572`. None of them reaches an assertion.

```
$ python -m pytest tests/test_aging_and_statements.py -q
25 failed in 9.91s
$ ... --tb=line | grep -oE "no such table: [a-z_]+" | sort | uniq -c
     57 no such table: credit_note_allocations
     18 no such table: credit_notes
```

The file builds its own in-memory SQLite and creates twelve tables by hand
(`Company` through `PaymentAllocation`). `SqlAlchemyReportRepository`'s aging
query LEFT JOINs two more -- `credit_notes` and `credit_note_allocations` --
to subtract credited amounts from the outstanding balance. That join and the
test file landed in the same commit; the fixture was never told.

**What is unverified because of it.** Every aging bucket (current, 1-30,
31-60, 61-90, 91-120, 120+), partial payment, void and draft exclusion,
as-of-date payment cutoffs, AR/AP direction filtering, multi-partner and
multi-currency isolation, company isolation, and the whole partner statement
-- opening balance, running balance, receipts, vendor payments, date-range
filtering, void payments, and multiple allocations against one invoice.
Nothing in the suite covers any of it, here or elsewhere.

It is invisible in the ordinary way: the full suite reports "25 failed, 1181
passed" and has for the whole of this branch, so the number is read as the
known-bad tail rather than as one file that has never worked.

**The fix is three lines** -- add `CreditNote.__table__` and
`CreditNoteAllocation.__table__` to the fixture's create list, and import
them. It is filed rather than done because the tests have never passed, so
what they assert is unverified too: turning them on is a review of 25
assertions, not a fixture edit.

**Where** `backend/tests/test_aging_and_statements.py`, `_session()`.

---

## RAG-18 · 24 lint errors in the subledger UI, and a frontend job that has never reached its build step

**Severity** Medium · **Measured** 2026-09-25, branch
`phase-61-subledger-and-agent` at `a0be8e1`, in CI · **Owner** whoever owns
phase-61

The first CI run this branch has ever had failed ESLint, and ESLint runs
fourth of seven steps in the frontend job. Everything after it is skipped, so
on this branch CI has never once evaluated the production build or either
test runner.

```
> eslint .
✖ 32 problems (24 errors, 8 warnings)
##[error]Process completed with exit code 1.

     ok        TypeScript type-check
     FAILED -> ESLint
     skipped   Vite production build
     skipped   Node built-in unit tests
     skipped   Vitest component/unit tests
```

`23 @typescript-eslint/no-explicit-any` and `1
@typescript-eslint/no-unused-vars`, across ten files:

| errors | file |
|---|---|
| 4 | `features/credit-notes/AllocateCreditNoteModal.tsx` |
| 4 | `features/credit-notes/CreditNotesPage.tsx` |
| 4 | `features/refunds/RefundsPage.tsx` |
| 3 | `features/refunds/NewRefundModal.tsx` |
| 2 | `features/credit-notes/NewCreditNoteModal.tsx` |
| 2 | `features/invoices/InvoicesPage.tsx` |
| 2 | `features/payments/PaymentsPage.tsx` |
| 1 | `features/invoices/NewInvoiceModal.tsx` |
| 1 | `features/partners/NewPartnerModal.tsx` |
| 1 | `features/payments/NewPaymentModal.tsx` |

All ten arrived with the WIP park (`e699ede`, `c6ba572` before the history
rewrite). `batch-1-deploy-correctness` passes ESLint at `bac5cf6`, which is
what dates them: they entered with that commit and nothing has run `eslint`
on this branch since.

**Why nobody noticed.** These workflows trigger on `pull_request` and pushes
to `main`. Neither branch had ever been pushed, so no run existed to be red.
Local verification on this branch ran `tsc -b`, Vitest and the backend suite
and never `npm run lint` -- and `tsc -b` is clean, so the type-check step
passes and the failure looks like it appears out of nowhere at step four.

**What the skipped steps actually do**, run locally at `a0be8e1` so the
unknown is at least written down:

```
npm run build       ✓ built in 35.10s      (see the caveat below)
node --test         4 passed, 0 failed
npm run test:run    29 files, 159 passed
```

So nothing behind the ESLint wall is broken today. That is a measurement of
one moment, not a guarantee: until ESLint is green, CI cannot tell anyone
when that stops being true.

**The build caveat.** `npm run build` fails on a developer machine that has
a `frontend/.env` pointing `VITE_API_BASE_URL` at localhost --
`vite.config.ts` refuses that for a production build. That is the guard
working. CI has no such file, and the build above was run with the local one
moved aside, which is how CI sees it.

**Not fixed here, deliberately.** A sweep replacing 23 `any`s across ten
files nobody on this branch wrote is a guess at what each was standing in
for. The one error that belonged to this branch's own work -- an unused
`metrics` binding in `GroundingCardKinds.test.tsx` -- was fixed in `a0be8e1`,
which is why the count is 24 and not 25.

**Where** `frontend/src/features/{credit-notes,invoices,partners,payments,refunds}/`,
and `.github/workflows/frontend-validation.yml` for the step ordering.

---

## RAG-19 · A correction is applied as its own opposite, and nothing says so

**Severity** Critical · **Measured** 2026-09-27, branch
`phase-61-subledger-and-agent` at `ba2fa62`, over HTTP and in process

A user correcting the assistant during a transaction clarification gets a
draft against **the account they just negated**. No warning, no "I did not
understand", no hedge -- a confirm button.

`_resolve_bank_cash_answer` scans for bank terms before cash terms and has no
notion of negation, so any reply containing both concepts returns the first:

```
  what the user typed              means                                   resolves to
  لا، خليها من الصندوق بدل البنك   no, make it from the CASH BOX, not bank  bank
  من الصندوق مش من البنك           from the cash box, not the bank          bank
  ليس من البنك، من الصندوق         not from the bank, from the cash box     bank
  مش البنك                         not the bank                             bank
  لا بنك                           no bank                                  bank
  from cash not bank               from cash not bank                       bank
  not bank, cash                   not bank, cash                           bank
```

Both languages. Every one is wrong.

**Why it is silent, and why that makes it Critical rather than High.** A
value *was* resolved, so `_apply_clarification_answer` returns
`changed=True`, and the `"لم أفهم إجابتك"` branch in
`_handle_pending_transaction_answer` never fires. The visible failure mode --
the loop the user complained about -- is the *safe* one. This is the unsafe
one: it proceeds confidently.

**Measured on the Yemen chart**, company 13116 `Acme Demo Trading`, which has
`1100 الصندوق`, `1110 بنك الكريمي` and `1140 محفظة جيب`. Turn 1 is
`دفعت 300 كهربا`; the assistant asks bank or cash; turn 2 varies:

| turn 2 | means | draft credits |
|---|---|---|
| `البنك` | the bank | `1110 بنك الكريمي` ✅ |
| `الصندوق` | the cash box | `1100 الصندوق` ✅ |
| `لا، من الصندوق مش من البنك` | **NOT the bank, from the cash box** | **`1110 بنك الكريمي`** ❌ |
| `من محفظة جيب` | from the Jeeb wallet (1140, real) | no draft -- clarification loop |

The correct answer is in the chart and resolves perfectly when said plainly.
Negating the wrong one returns it.

Over HTTP as an admin on the English demo chart, same shape:

```
POST /ai/gemini-assistant  "لا، من الصندوق مش من البنك"
  intent           : create_journal_draft
  suggested_action : create_journal_entry_draft
    5000 Expenses    debit=300.0  credit=0.00
    1110 Main Bank   debit=0.00   credit=300.0
```

**What does not save it.** Every downstream check passes, because the entry
is *valid* -- it is just wrong. `1110` is a real, active, company-scoped
account; the entry balances; the role is admin; the period is open. Balance
validation, account resolution and `/confirm-action`'s role re-check all
protect against an *invalid* entry and none of them can see a *misattributed*
one. That is the correct division of labour and not a defect in those
guards; it is why understanding cannot be left to substring order.

**Blast radius.** Any clarification turn where the user corrects rather than
answers -- which is the single most likely moment for that phrasing. The
result is a draft, not a posted entry, so a human sees it before it becomes
a ledger row. That is the only thing holding this below "it silently posts".

**Not fixed here, deliberately.** Reordering the two scans or adding a
negation list would move the failure rather than remove it: the next
phrasing that carries two concepts breaks the same way. The fix belongs
inside the understanding/authority redesign, where a reply containing a
negation marker or more than one candidate concept is by definition not
unambiguous and is interpreted rather than matched.

### Status 2026-09-28 — still open, and why

The redesign has landed in three commits and this finding is **not closed**,
because the table that would close it is incomplete.

* `6fda7eb` made every phrasing above **unreachable** by the buggy resolvers.
  A silent wrong entry became a visible re-ask. That is the safe failure
  mode, not the fix.
* `2064479` put the three trust boundaries in the prompt first.
* The interpreter now resolves the escalated replies. Measured end to end on
  company 13116: `محفظة ون كاش` and `ون كاش` produce **1130**, `من محفظة جيب`
  produces **1140**, `not bank, cash` produces **1100**. Abandonment
  discards the pending token; an unreadable reply asks a free-form question.
  All eight option/ordinal/plain answers still resolve with **0 provider
  calls**, counted rather than assumed.

**What is unverified.** Four of the Arabic negation phrasings and the bare
`جيب` have not been shown resolving, because the Gemini free tier's daily
cap stopped the run:

```
429 RESOURCE_EXHAUSTED
quotaId: GenerateRequestsPerDayPerProjectPerModel, limit: 20,
model: gemini-3.6-flash
```

Those five fell back to the deterministic re-ask, which is the designed
behaviour under an unavailable provider and is itself worth having measured
— but it is not evidence that they interpret correctly. **This finding
closes when those five are shown producing the account the user meant, on a
day with quota, and not before.**

### Status 2026-09-29 — one more row verified, four still not

| reply | means | got |
|---|---|---|
| `لا، خليها من الصندوق بدل البنك` | not the bank — the cash box | **1100 الصندوق** ✓ |

The first Arabic negation phrasing is verified. It resolved on 2026-09-28, in
the two requests that got through before the cap closed again.

The remaining four — `من الصندوق مش من البنك`, `ليس من البنك، من الصندوق`,
`from cash not bank` and the bare `جيب` — have now failed to run on two
separate days. Both times the interpreter returned `None` for a **provider
error**, not for a wrong answer: on 2026-09-29 two rows raised `ServerError`
(a 5xx from Google) and two raised `ClientError`, and a raw call made
immediately after returned

```
429 RESOURCE_EXHAUSTED  metric: generate_content_free_tier_requests
limit: 20, model: gemini-3.6-flash
Please retry in 43.9s
```

**A caveat on every call count in this file.** The counter used throughout
wraps `genai.Client.__init__`, so it counts client *constructions*, not HTTP
requests. A row reported as `calls=1` is one client and at least one request;
if the SDK retries internally — which the two `ServerError` rows make likely —
it is more. The `calls=0` figures are unaffected: no client is built, so no
request is issued, and the "instant and free" claim stands. The `calls=1`
figures may undercount, and a sub-minute retry hint against a limit of 20 is
hard to reconcile with four counted calls unless they do.

**Still open.** Four rows, and now also the question of what the real request
count is.

### A second case, same root cause: a real account name read as a generic concept

Found while modelling the fix, and it is not a negation at all. The chart has
`1130 محفظة ون كاش` (the OneCash e-wallet). The cash keyword list contains
`كاش`. So naming the wallet matches the generic cash concept by substring,
and the wallet loses to the cash box:

| turn 2 | means | draft credits |
|---|---|---|
| `ون كاش` | the OneCash wallet (1130) | **`1100 الصندوق`** |
| `محفظة ون كاش` | the OneCash wallet (1130) | **`1100 الصندوق`** |

Silent again -- a value resolved, so `changed=True` and no warning. Measured
on company 13116, same two-turn sequence.

This matters for the fix as much as the negation case does. It shows the
ambiguity test cannot be a fixed word list: `كاش` is unambiguous as a word
and ambiguous as soon as the chart contains an account whose name contains
it. Any detector that decides "unambiguous" without consulting this
company's accounts will keep making this class of error.

**Where** `gemini_assistant_service._resolve_bank_cash_answer`,
`_resolve_transaction_type_answer` (same shape), and the `changed` flag in
`_apply_clarification_answer` that suppresses the fallback.

---

## RAG-21 · The free path's correctness depends on a field-name agreement that nothing asserts

**Severity** Medium · **Measured** 2026-09-28, branch
`phase-61-subledger-and-agent`, commit `9aee18d`

Filed as a structural finding, and deliberately filed even though the commit
that follows removes today's instance of it. The instance is not the finding.

Four places branch on the name of the field being clarified —
`clarification_ambiguity._concepts_present` decides which concepts are
candidates, `_resolve_transaction_type_answer` decides which transaction type
a term means, `clarification_interpreter.FILLABLE_FIELDS` decides what the
model may fill, and `_apply_interpreted_reply` decides what an accepted
interpretation writes. (This entry first said three; the fourth was found by
the deletion sweep, which is itself the finding.) A fifth,
`_missing_fields_for`, decides which names are ever produced. **Nothing checks
that they agree**, and the ways they disagree are not symmetric:

| disagreement | consequence |
|---|---|
| a name the detector knows and the resolver does not | RAG-20: certified, unreadable, re-ask |
| a name produced but unknown to the detector | no concepts found, so **every** reply to that question escalates — the free path dies silently, and only the quota bill would say so |
| a name known to both but outside the question asked | the resolver answers a question that was not asked |

Today's instance is the third: `_resolve_transaction_type_answer` returns
`supplier_payment` for `مورد` even when the question asked was
`customer_or_income`. That is harmless **only** because
`_missing_fields_for` never emits that name — a safety property that lives in
a different function, is stated nowhere, and would be silently lost by a
one-line change there.

**Confirmed by sweep, not by reading**, because a deletion is the claim that
costs if wrong. Two independent sweeps:

*Static* — every call that can write a pending envelope's `missing_fields`,
enumerated from the AST of the whole `backend/app` tree, with the source text
of each argument: seven sites, all in `gemini_assistant_service`, all
resolving to `_missing_fields_for`'s return, a literal list in
`_handle_action_request`, or a re-circulated `pending.missing_fields`. The
closed set of producible names is `{payment_source, receiving_account,
transaction_type, account_mapping}`. Every occurrence of the two suspect
names anywhere in the tree is in a *consumer* position — `Set`, `Compare` or
`Tuple` used for membership — and none in a producer position. Also checked:
the orchestrator has its own separate vocabulary (`AssistantMissingField`, a
closed `Literal` using `receipt_destination` where this path uses
`receiving_account`) and `gemini_assistant_service` never reads
`decision.missing_fields`, so it cannot leak in from there.

*Runtime* — the whole suite, spied: `payment_source` only, as recorded under
RAG-20.

### A live instance of the second row: `account_mapping`

Found while writing the invariant test, and not removed by deleting the dead
names. `_missing_fields_for` returns `["account_mapping"]` as its fallback. No
consumer branches on that name, so `_concepts_present` finds no candidate
concepts for it. Measured, every reply shape against a Yemen-shaped chart:

| reply to an `account_mapping` question | detector | resolved |
|---|---|---|
| `1` / `2` / `الأول` | instant, `option` | **nothing** |
| `البنك` / `الصندوق` / `محفظة ون كاش` | escalate, `named_account_no_concept` | nothing |
| `bank` / `مورد` | escalate, `no_match` | nothing |

For that question the instant path cannot answer anything. Every reply either
escalates — a provider call each, where the same reply to a bank/cash question
costs none — or is certified and resolves nothing. The option rows are RAG-20's
shape again, three more of them; their severity is lower only because this
question carries no options the user could have been offered
(`_clarification_options_for_missing_fields` returns `[]` for it). Recorded
rather than fixed, because the question is "which account?", not "bank or
cash?", and giving it a resolver is different work.

### What the invariant test catches, and what it still cannot

`backend/tests/test_clarification_resolver_agreement.py` asserts row 1 in
full: over a 1,574-reply corpus, closed over both option sets, all six
vocabulary lists and the chart, no reply the detector certifies is one the
resolver behind that field answers `None` to. Between 527 and 640 replies are
certified per field, so the assertion is nowhere near vacuous, and
`test_the_invariant_bites_when_the_option_sets_are_pulled_apart` reproduces
the pre-fix resolver and requires the invariant to fail on exactly the three
replies RAG-20 names.

It also asserts **part of row 2**: the set of producible field names must
equal the set that has a resolver plus an explicitly recorded gap set. That is
what makes `account_mapping` visible above instead of invisible, and it means a
newly produced name with no consumer fails a test rather than quietly doubling
the provider bill.

It does **not** cover row 3. A resolver answering a question that was not
asked returns a value, so the invariant passes and the value is wrong. The
assertion that would catch it — that each consumer's branch set is confined to
the question actually asked — does not exist. **This finding stays open on that
row, and on `account_mapping`.**

**Where** `gemini_assistant_service._missing_fields_for` (the producer), and
`clarification_ambiguity._concepts_present`,
`gemini_assistant_service._resolve_transaction_type_answer`,
`gemini_assistant_service._apply_interpreted_reply` and
`clarification_interpreter.FILLABLE_FIELDS` (the four consumers).

---

## RAG-22 · The first turn offers two accounts without asking whether the company has them

**Severity** Major · **Measured** 2026-09-28, branch
`phase-61-subledger-and-agent`, commit `45e5786`

Reported from a live click-through in *Demo Company Ltd* (15449), whose chart
has a bank account and **no cash account at all**:

```
  turn 1  دفعت 300 كهربا
          🤔 هل تم دفع 300.00 من البنك أم الصندوق؟   1. البنك   2. الصندوق
  turn 2  2
          Recognized intent (expense_payment) but couldn't match the
          required accounts. Please create the entry manually.
```

Option 2 names an account the company does not have, and choosing it dead-ends
the entry the user was in the middle of making.

### The options are fixed in code, not derived from the chart

Measured by running the identical turn-1 message against both companies and
comparing what came back. No provider calls, counted:

| company | cash accounts in chart | options offered |
|---|---|---|
| 15449 Demo Company Ltd | **NONE** | `[('البنك', 'bank'), ('الصندوق', 'cash')]` |
| 13116 Acme Demo Trading | `1100 الصندوق` | `[('البنك', 'bank'), ('الصندوق', 'cash')]` |

Identical. The structural proof is the signature:
`_clarification_options_for_missing_fields(missing_fields, language)` takes
**no accounts argument**, so it cannot consult the chart even in principle.
The same pair builds the question text through
`_clarification_question_for_missing_fields`, so the sentence and the buttons
are wrong together.

### The path is sound; only the option is wrong

Measured in the same company, same turn 1:

| turn 2 | result |
|---|---|
| `1` (bank — exists) | drafts **`1110 Main Bank`**, correct |
| `2` (cash — does not exist) | the failure message above |

So this is not a broken clarification path. It is one offered option that no
account can satisfy. A user who happens to pick the other one never sees it.

### Why this is wider than RAG-19

RAG-19 and RAG-20 are about reading the user's **reply**. This is about what
the assistant **says first**, before the user has typed anything, and it is
wrong for every company whose chart lacks one of the two hard-coded concepts.
The ambiguity detector added in `6fda7eb` reads the live chart precisely so
that "cash" is judged against this company's accounts — and the question that
provokes the reply still does not.

Note the detector inherits the blind spot in a second way: for a reply naming
a concept with no matching account, `_concepts_present` still reports the
concept, because it is keyed on the vocabulary rather than on the chart.

**Not fixed here.** Deriving the options from the chart changes what every
clarification question says, and a company with several cash accounts, or
none, or only wallets, each need an answer. That is design work, not a patch.

**Where** `gemini_assistant_service._clarification_options_for_missing_fields`
(no `accounts` parameter), `_clarification_question_for_missing_fields`, and
the `len(lines) < 2` guard at `_build_preview` that produces the dead end.

### A second, separable problem in the same exchange: the reply's language

The failure message arrived in **English inside an all-Arabic thread**. This is
**not** a missing translation. Both sites that build it carry an Arabic form —
`gemini_assistant_service.py:2225` and `:2604` — and the Arabic form was
reproduced simply by changing what the request carried:

```
request language='en'  -> "Recognized intent (expense_payment) but couldn't match…"
request language='ar'  -> "تم التعرف على النية (expense_payment) لكن لا يمكن مطابقة الحسابات."
```

Turn 1 answered in Arabic in **both** runs, because that message contains
Arabic. So one exchange answered turn 1 in Arabic and turn 2 in English.

This is **N24 as filed** — language is re-detected per message at
`dispatch_gemini_assistant` (`language = detect_message_language(message, language)`)
— with a subcase worth recording: `"2"` carries *neither* script, so
`detect_message_language` returns its **fallback**, and the fallback is the
language the request carried, which is the UI's language toggle rather than
the thread's language.

```
detect_message_language('2', fallback='en') -> 'en'
detect_message_language('2', fallback='ar') -> 'ar'
```

So a user with the UI in English who types Arabic gets Arabic answers to every
message containing Arabic letters and English answers to every bare number,
ordinal or digit — which is exactly the set of replies the clarification
options invite. The fix is not a translation; it is deciding whether a thread
has a language that a scriptless reply should inherit.

---

## How to read the basis column

Every entry says what it rests on, because they do not all rest on the same
thing and pretending otherwise is how a guess gets treated as a measurement.

* **MEASURED** -- something was run and the result is recorded in the entry.
  Where the run was repeated on 2026-09-26 at `bac5cf6`, the entry says so;
  that is the difference between "was true once" and "is true now".
* **READING-ONLY** -- established by reading the code, never executed. The
  mechanism is visible in the source; the consequence is inferred. Re-measure
  before acting.
* **ID ONLY** -- the substance did not survive. The ID and a one-line gist
  are all there is, because the finding was measured in a conversation and
  the detail was never written down. **These are not filed findings.** They
  are a list of things to re-investigate from scratch, recorded so that the
  IDs stop looking accounted for.

An **ID ONLY** row is a failure of record-keeping, not a finding. It is here
because a missing entry is invisible and a row that admits it is not.

---

# Part 1 -- the backlog carried forward

These were measured during the audits and never acted on. None has a
reproducible write-up elsewhere; this is their first durable record.

## Security and authentication

| ID | Finding | Basis |
|---|---|---|
| **B4** | `GET /company-users/invitations/validate` takes a token and runs a bcrypt comparison with no authentication and no rate limit, so it is an unauthenticated CPU-cost endpoint. | **MEASURED**, re-run 2026-09-26: the endpoint's dependency list contains 0 auth or limiter dependencies (`company_user_routes.py:184`). |
| **B6** | The access token lives in `localStorage` with a 24 h lifetime, readable by any script on the origin. | **MEASURED**, re-run 2026-09-26: `frontend/src/auth/token.ts` reads and writes it there. Whether 24 h is the right lifetime is a product decision, not a defect. |
| **B8** | No dependency vulnerability scanning of any kind. | **MEASURED**, re-run 2026-09-26: no `dependabot.yml`, and no `pip-audit`, `safety`, `trivy` or `snyk` anywhere under `.github/`. |

**B7 is not in the table above, and that is this merge's doing.** It was open
on `batch-1-deploy-correctness` and closed on `phase-61-subledger-and-agent`;
merging the two brings the fix into the same tree as the entry, so it is
closed here. Its record is the `† B7` section of `closed-findings.md`, which
carries more than this row did: the claim as filed is false in both callers
and is asserted against, and the more serious half -- that `build_agent_prompt`
carried no untrusted-text notice at all -- was never filed under B7 or any
other ID.

The row also carried the only cross-reference in this file to **RAG-6**, which
is kept here so the merge loses nothing: RAG-6 closed the tool-result half of
the same labelling problem, and B7 was the conversation-history half. RAG-6 is
in `closed-findings.md`'s Fixed table (`89cbbe9`).

## Correctness

| ID | Finding | Basis |
|---|---|---|
| **A7** | `POST /fiscal/quick-setup-today` can choose a `period_no` that already exists, rather than failing or picking the next free one. | **READING-ONLY.** The selection is visible in `fiscal_routes.py`; no colliding request was ever issued. |
| **A8** | `send_conversation_message` dereferences a conversation that may have been deleted between the lookup and the write. | **READING-ONLY.** Never raced in practice. |
| **N8** | A company-users page's row count and its paginator describe different sets: `total` counts one thing and the rows shown are filtered by tab. | **READING-ONLY.** Described in `bbdca65`'s message, where N7 and N9 were fixed and this was explicitly left. |
| **N13** | Opening balance renders as `"0"` where its siblings render `"0.00"`. | **READING-ONLY.** Recorded in `3d76fda` and deliberately not fixed there, because fixing it changes captured output and needs its own before/after. |

## The assistant's classifier and handlers

All four MEASURED rows below were re-run on 2026-09-26 at `bac5cf6`; the
literal returns are in the table.

| ID | Finding | Basis |
|---|---|---|
| **N20** | The audit keyword list contains no Arabic word for "audit", so the obvious Arabic phrasing never reaches the audit handler. | **MEASURED**: `_classify_intent("اعرض سجل التدقيق")` -> `unknown`. The only Arabic route in is "last activity". |
| **N21** | The classifier has no "who reversed" pattern, so that question is classified as an audit question and reaches the right handler only because the orchestrator re-routes it. | **MEASURED**: `_classify_intent("Who reversed the entry?")` -> `audit_question`. |
| **N23** | `trace_question` cannot trace zero: the classifier and the amount extractor disagree about the same message. | **MEASURED**: `_is_exact_amount_trace_request("trace 0")` -> `False`, `_extract_amount_from_message("trace 0.00")` -> `None`. |
| **N24** | The `language` argument loses to the message: the dispatcher re-detects language from the text, so `language="en"` answers an Arabic question in Arabic. | **MEASURED**: `detect_message_language("ما هو الربح؟", "en")` -> `ar`. Arguably correct behaviour, but it is not what the parameter says. |
| **N22** | `who_action`'s reply describes the **newest** audit log whatever filter it asked for; it never checks that what came back matches the question. | **READING-ONLY.** The missing check is visible in the handler. Not re-verified. |

Three more are open but **held still on purpose**, which is a different state
again:

| ID | Finding | Basis |
|---|---|---|
| **N17** | `pl_contribution_question` answers `intent="answer_journal_question"` -- the same string `journal_question` uses, so a caller cannot tell the two apart. | **MEASURED** and pinned. |
| **N18** | The same handler reports `confidence="high"` and `status="grounded"` on an empty result, where every sibling reports `low`. | **MEASURED** and pinned. |
| **N19** | The same handler fills `grounding.entries` but leaves `reply.evidence` empty, where `trace_question` fills both. | **MEASURED** and pinned. |

"Pinned" means `backend/tests/test_assistant_handler_characterisation.py`
asserts the current behaviour deliberately, so that a refactor changing one
fails instead of passing quietly. **Do not "fix" these by editing the
assertion.** Change the behaviour and the assertion together, in a commit
that says which of the two was wrong.

## Performance

| ID | Finding | Basis |
|---|---|---|
| **C4** | The chart-of-accounts seed makes two database round trips per account. | **READING-ONLY.** Never timed. Bounded work at a known size, which is why it outranked nothing else. |

## Structure and dead weight

| ID | Finding | Basis |
|---|---|---|
| **E5** | The semantic intent classifier is unreachable: nothing constructs one. | **MEASURED**, re-run 2026-09-26: 0 route modules pass `semantic_intent_classifier=`. The dispatcher accepts the parameter and every caller leaves it `None`. |
| **E8** | A very long orchestration handler sits in the route layer. | **MEASURED**, re-run 2026-09-26, and the original number was wrong by more than it was right. Three handlers now exceed 150 lines: `ai_routes.py:169 gemini_assistant_confirm_action_endpoint` **228**, `fiscal_routes.py:666 quick_setup_fiscal_period_for_today` **239**, `fiscal_routes.py:499 update_fiscal_period_endpoint` **156**. The finding said "244-line" and named one. |
| **E2** | An unused clean-architecture audit layer. | **READING-ONLY, and partly contradicted.** Re-checked 2026-09-26: `app/application/audit/` holds only `README.md`, `__init__.py`, `dto.py` and `ports.py` -- no use cases -- but `app/infrastructure/audit/audit_adapter.py` does import `application.audit.dto`, so it is not unused. Whatever was measured, "unused" is too strong. **Re-measure before deleting anything.** |
| **E4** | Five journal hooks are the same forty lines. | **READING-ONLY.** Which five was never written down; a reader can find them, but this entry does not name them. |
| **N1** | `Mapped["User"]` is a forward reference no static tool can resolve. | **MEASURED**, re-run 2026-09-26: `models/company_user.py:48`. |
| **N2** | `credit_match` is computed and never used. | **MEASURED**, re-run 2026-09-26: one assignment, no reads, in `gemini_assistant_service.py`. |
| **N3** | `acc_map` is built and never used. | **MEASURED**, re-run 2026-09-26: same file, same shape. |
| **N4** | One `== True` comparison lacks the `# noqa: E712` its three siblings carry, so the file is inconsistent about the same idiom. | **MEASURED**, re-run 2026-09-26: `company_user_routes.py:332` bare; lines 112, 113 and 397 annotated. |
| **N5** | Three repositories import a Protocol they do not implement. | **READING-ONLY, and not re-verifiable here.** Which three was never recorded, and `ruff` is not installed in this checkout, so the original count cannot be reproduced. Closer to ID ONLY than the rows above. |
| **N6** | 53 module-level imports appear after code (E402). | **READING-ONLY, and not re-verifiable here.** Same reason: the count came from a `ruff` run and `ruff` is not installed. The number should be treated as indicative. |
| **N10** | The account picker cannot see past 500 accounts. | **READING-ONLY.** Re-checked 2026-09-26 and **the component could not be located by search**, so this may have moved or gone. Re-measure before acting. |

## Operations

| ID | Finding | Basis |
|---|---|---|
| **F3** | No logging configuration: the application never configures logging, so it inherits whatever the host provides. | **MEASURED**, re-run 2026-09-26: 0 `dictConfig` or `basicConfig` call sites under `app/`. |
| **F4** | No graceful shutdown: nothing drains in-flight work on SIGTERM. | **MEASURED**, re-run 2026-09-26: no `lifespan` and no shutdown handler in `app/main.py`. |
| **G1** | `restore_admin.py` sits at the backend root, where an operational script does not belong. Downgraded to Low because its production guard fires. | **MEASURED**, re-run 2026-09-26: the file is still there. The severity half is settled; the tidiness half is this entry. |

---

# Part 2 -- IDs whose substance did not survive

**These are not findings.** Each was measured in a conversation and never
written down, so all that remains is an ID and a gist. They are listed so
that the IDs stop appearing accounted for, and so the next person re-opens
them deliberately rather than trusting a sentence nobody can source.

| ID | All that survives | Why it cannot be reconstructed |
|---|---|---|
| **G2** | "An unguarded script that dumps every user's email." | No script under `backend/scripts/` obviously matches (checked 2026-09-26: `bootstrap_platform_admin`, `cleanup_local_demo_data`, `manage_company_subscription`, `onboard_client`, `production_preflight`, `reset_company_data`, `seed_demo_data`). Either it was renamed, removed, or the finding meant something narrower. **Re-audit the scripts directory.** |
| **G3** | "Six dead service functions, later corrected to five." | The functions were never named. Finding them again means a fresh reachability pass. |
| **G4** | "Seven modules past their named deletion phase." | The modules were never named, and no module under `app/` self-labels a deletion phase today (grepped 2026-09-26: 0 hits). Either the labels were removed or they were never in the source. |

---

# Part 3 -- re-scoped, and recorded elsewhere

These were downgraded, narrowed, withdrawn or corrected rather than fixed, so
they have no closing commit. Their record is `docs/closed-findings.md`, in the
"Withdrawn, downgraded, or corrected" section: **A3** (Medium to Low, one tab
only), **D1** (High to Medium, the query framing was wrong), **D4**
(narrower; the real case became N10), **E7** (Medium to Low; zero-admin is
not sequentially reachable), **I3** (over-claimed: one of four validated).

They are cross-referenced here because a reader checking whether an ID is
open should not have to know which of two files to open first.
