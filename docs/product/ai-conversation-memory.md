# AI Conversation Memory

Why the assistant used to ask *"which transaction do you mean?"* one second
after the user had said exactly which transaction they meant, and what now
carries a subject across two turns.

## The problem

The assistant was not amnesiac in the storage sense. Conversations, and every
message in them, have been persisted per user and per company for some time —
reopening the panel reliably showed the transcript. What was missing is that
nothing *read* that transcript when interpreting the next message.

A user types two turns the way people actually talk:

```
user:      I paid the office rent
assistant: How much was it, and what did you pay from?
user:      it was 300 from the bank
```

Read on its own, the third line has no subject. It is not a report question, it
names no expense, and the intent orchestrator classified it as `unknown` and
returned a safe clarification: *"Which accounting question would you like help
with?"* The user had answered that question in the previous line, so from their
side the assistant had forgotten it.

## What memory means here

Two separate mechanisms, both scoped the same way:

| Layer | Where it lives | What it is for |
| --- | --- | --- |
| Persisted transcript | `assistant_conversations` / `assistant_messages` | Reopening a thread and reading it back |
| Follow-up merging | `build_followup_message` | Understanding the *current* message |

Only the second is new. The first already existed and is unchanged.

## Follow-up merging

`build_followup_message` (in `gemini_transaction_parser.py`) joins the newest
user turns with the message being interpreted:

```
"I paid the office rent" + "it was 300 from the bank"
  → "I paid the office rent. it was 300 from the bank"
```

The merged string parses cleanly as an expense payment of 300 from a bank
account, so the assistant drafts the entry instead of asking again.

Three deliberate limits:

- **Only user turns are merged.** Assistant replies quote amounts from earlier
  drafts (*"I can draft an entry for 999"*), and merging them would let a number
  the user never typed reach amount extraction.
- **At most `MAX_FOLLOWUP_TURNS` (2) previous turns.** Merging the whole thread
  would let a transaction from ten minutes ago resurface as the subject of an
  unrelated message.
- **Each turn is truncated and stripped of control characters** before it is
  merged or placed in a prompt, so a long or crafted turn cannot crowd out the
  rest of the prompt.

## Where it takes effect

Two places in `dispatch_gemini_assistant`, both guarded by
`_is_memory_actionable_followup` — which is true only when the merge produces a
*different* string that reads as an accounting message with an amount:

1. **Before the safe-clarification bail-out.** The intent orchestrator returns
   `safe_clarification` for a message it cannot classify. That gate now lets a
   memory-actionable follow-up through instead of ending the turn. This is the
   fix for the symptom above.
2. **Before the final unknown reply.** A last attempt at the action handler,
   accepted only if it produced a real draft or a specific clarification.

Inside `_handle_action_request`, the merged message is used as a *second* parse
attempt: the message is always parsed on its own first, and the merged version
is only tried when the standalone parse produced nothing actionable. A message
that stands on its own is therefore never reinterpreted through its history.

The recent turns are also passed to the semantic parser as
`bounded_recent_conversation` inside the trusted-data block, so a provider-backed
parse sees the same context the deterministic path does.

## Isolation

Memory is never global. Every boundary that applied to the stored transcript
applies unchanged to follow-up merging, because the merge only ever sees the
history the conversation service already handed to the dispatcher.

| Boundary | Guarantee |
| --- | --- |
| Company | A conversation belongs to one `company_id`; history is read with that filter. Two companies of the same user share nothing. |
| User | A conversation belongs to one `user_id`. A colleague in the same company gets 404 on the thread and never sees it listed. |
| Thread | History is read with `conversation_id == this thread`, so a new thread starts genuinely blank. |

`tests/test_assistant_conversation_memory.py` asserts each of these three
directly, including the negative case: the same follow-up sent with no
preceding turn must *not* draft an entry.

## What did not change

- The confirmation step. A remembered follow-up produces a **draft**, which the
  user still confirms before any journal entry exists.
- Date safety. Non-today dates are still refused for drafts.
- The transcript UI. Listing, restoring, renaming, archiving and deleting
  conversations behave exactly as before.
