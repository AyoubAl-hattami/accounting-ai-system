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
See the caveat at the top of `closed-findings.md` before matching an ID.

An entry earns its place by being **measured**. Each one states what was run
and what came back, so the next person can reproduce it before deciding
whether it matters. An entry with a plausible story and no measurement is a
guess and does not belong here.

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

## RAG-20 · The detector certifies replies the resolver behind it cannot read

**Severity** Major · **Measured** 2026-09-28, branch
`phase-61-subledger-and-agent`, commit `9aee18d`

The ambiguity detector short-circuits an exact option match as unambiguous
and sends it down the instant path, where a resolver reads it. The two
disagree about what an option is. `clarification_ambiguity`'s `OPTION_FIRST`
and `OPTION_SECOND` include `واحد`, `اتنين` and `اثنين`;
`_resolve_transaction_type_answer` restates its own literal sets and does
not. So the detector says "a pattern may read this", the pattern returns
`None`, `changed` stays `False`, and the user gets **"لم أفهم إجابتك" plus
the same two options again** — the failure this whole redesign exists to
remove, arriving through the part of it that was supposed to be provably
safe.

**Measured**, by sweeping every reply in both option sets and every term in
all six vocabulary lists against all four question fields (pure functions, no
provider):

```
replies the detector passes that the resolver cannot read: 9
  واحد / اتنين / اثنين  ×  transaction_type
                        ×  supplier_or_expense
                        ×  customer_or_income
```

### Reachability: 3 of the 9, and no test covers them

`_missing_fields_for` emits only `payment_source`, `receiving_account`,
`transaction_type` and `account_mapping`. The other two field names are
produced nowhere (see RAG-21 and the sweeps recorded there), so six of the
nine rows sit behind names that never occur. The three `transaction_type`
rows are reachable in production: that name is appended whenever
`parsed.transaction_type == "unknown"`.

A runtime sweep of the **whole backend suite**, recording every field name
handed to the detector, to `_apply_clarification_answer` and to
`_pending_from_parsed`, saw exactly one:

```
  clarification_ambiguity       -> payment_source
  _apply_clarification_answer   -> payment_source
  _pending_from_parsed          -> payment_source
  _resolve_transaction_type_answer -> never called
```

So the type resolver's dispatch has **no in-process test coverage at all**,
which is why nine holes could sit in it unremarked. (Limit of that sweep:
spies live in the pytest process, so the 39 HTTP files exercising the server
process are not covered by it. The static enumeration under RAG-21 is the
primary evidence for what can be produced; this corroborates it in-process.)

### Not a regression, and that matters for how it is fixed

Before the detector existed, `واحد` on a type question also fell through to
the re-ask — the resolver has never read it. What is new is that escalation
now exists and would read it correctly, and the option short-circuit is what
prevents that. This is a **missed rescue**, not a break. It is filed Major
rather than Critical for the same reason: the outcome is a visible re-ask,
not a silent wrong entry.

**The durable fix is not the harmonised list.** One option set closes these
nine. The invariant that closes the class is: *for every reply the detector
calls unambiguous, the resolver behind that field must return a value.*
Without it, the next word added to either side reopens this silently, and
nothing in the suite would notice — as nothing did.

**Where** `clarification_ambiguity.OPTION_FIRST` / `OPTION_SECOND` versus the
literal sets in `gemini_assistant_service._resolve_bank_cash_answer` and
`_resolve_transaction_type_answer`; the short-circuit at
`clarification_ambiguity.clarification_ambiguity`, the `option` branch.

---

## RAG-21 · The free path's correctness depends on a field-name agreement that nothing asserts

**Severity** Medium · **Measured** 2026-09-28, branch
`phase-61-subledger-and-agent`, commit `9aee18d`

Filed as a structural finding, and deliberately filed even though the commit
that follows removes today's instance of it. The instance is not the finding.

Three modules branch on the name of the field being clarified —
`clarification_ambiguity._concepts_present` decides which concepts are
candidates, `_resolve_transaction_type_answer` decides which transaction type
a term means, and `clarification_interpreter.FILLABLE_FIELDS` decides what
the model may fill. A fourth, `_missing_fields_for`, decides which names are
ever produced. **Nothing checks that those four agree**, and the ways they
disagree are not symmetric:

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

**Where** `gemini_assistant_service._missing_fields_for` (the producer),
`clarification_ambiguity._concepts_present`,
`gemini_assistant_service._resolve_transaction_type_answer`, and
`clarification_interpreter.FILLABLE_FIELDS` (the three consumers).
