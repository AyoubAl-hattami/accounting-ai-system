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
