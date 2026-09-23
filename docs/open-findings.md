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
