# Open findings

Findings that have been measured and not yet fixed.

Fixed findings are not listed here: their record is the commit that closed
them, which carries the ID in its subject (`[RAG-1]`, `[D2]`, `[A9]`, and so
on). This file exists for the other kind -- the ones found while looking for
something else, which otherwise survive only in a conversation.

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

## RAG-15 · Four of the six grounding cards are built, stored, and thrown away

**Severity** Medium · **Measured** 2026-09-24, branch
`phase-61-subledger-and-agent` at `a558d37`

`GroundingCards.valid()` accepts `profit_and_loss` and `journal_evidence`
and returns `null` for everything else. The backend has been emitting four
other kinds the whole time.

Rendered against the real component, one card per kind, all `status:
"grounded"` with real figures:

| kind | rendered |
|---|---|
| `profit_and_loss` | 2,229 characters |
| `journal_evidence` | 1,456 characters |
| `balance_sheet` | **nothing** |
| `trial_balance` | **nothing** |
| `general_ledger` | **nothing** |
| `account_ledger` | **nothing** |

**What a user lost.** Ask "what is our profit this month?" and the answer
carries a card: the three figures, the period, a "Verified from accounting
data" badge, and a button that opens the report. Ask "show me the balance
sheet", "show me the trial balance", "show me the general ledger" or "show
me the ledger for account 1110" and the same assistant, having run the same
kind of report through the same services, shows a paragraph of text and
nothing else. No badge, no figures table, no link. The answer is as verified
as the one that displays a badge; it just cannot say so.

It is worse now than it was. As of the card commits on this branch, those
four kinds are also produced by the tool path and pass the grounding gate --
so the backend has more verified cards than ever and the panel still drops
four of them on the floor.

**How long.** `GroundingCards` shipped on 2026-07-14 handling two kinds. The
four structured groundings arrived two days later, on 2026-07-16, with the
structured report handlers. The component has been edited once since and the
gap was not noticed, because nothing fails when a card is dropped -- the
reply still renders, one `return null` earlier.

**Where** `frontend/src/features/ai/GroundingCards.tsx`, `valid()`.

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

