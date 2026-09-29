# Closed findings

The other half of `open-findings.md`. That file holds what is measured and
still true; this one holds what was measured and is no longer true, plus the
findings that turned out to be wrong.

Its reason for existing is narrow. The commit that closes a finding carries
the ID in its subject, so `git log --grep` already finds any one of them --
but only if you already know the ID. This file is the index that makes the
IDs findable, and it is where a withdrawn or downgraded finding survives at
all: those have no closing commit, so without a row here they exist only in
a conversation.

**Evidence basis** is how the closure was shown, not how the finding was
first suspected. `RV` marks a row re-verified against the working tree at
`d516762` rather than taken from the closing commit's own measurement.

---

## A caveat about numbering, before you match an ID to anything

There are **two** finding numberings in this repository and they do not
correspond.

* `audit-report/Accounting_AI_System_Technical_Audit.md`, Appendix C,
  indexes **F-001 through F-025**. That is the earlier static audit.
* This file and `open-findings.md` use the **A / B / C / D / E / F / G / I**,
  **N** and **RAG** series, which came out of the later measured audits.

`F2` in this file is the process-local rate limiter. `F-002` in the audit
report is audit atomicity. They are not the same finding and the prefixes
collide by accident.

**No cross-walk between the two exists.** Nobody has mapped F-001…F-025 onto
these IDs, in this file or anywhere else, so an F-00x that looks closed here
is not closed -- it has not been looked at under that number. Building that
mapping is a real piece of work and remains undone.

---

## Fixed

| ID | Finding | Evidence | Commit |
|---|---|---|---|
| A1 | Fiscal period dates movable under posted entries | HTTP | `f0f0573` |
| A2 | Concurrent duplicate `entry_no` returned 500, not 409 | 12/12 over HTTP | `785ca83` |
| A4 | Dashboard hid failed sources; the error state was unreachable | test | `25772a2` |
| A5 | "Log in to accept" lost the invitation | test | `2668ad6` |
| A6 | `bootstrap_platform_admin --generate-password` could strand a superuser | test | `c485962` |
| A9 | `ProtectedRoute` rendered gated pages on an unresolved role | test | `ced3359` |
| B1 | Client-supplied `X-Forwarded-For` reached the login limiter | measured | `2bdc35c`, `6924145` |
| B2 / I1 | Alembic ignored `DATABASE_URL` for a hardcoded localhost | run | `cb96e52` |
| B3 | `POST /company-users` enumerated any platform user's email | HTTP | `fdc44a5`, `c9f60fb` |
| B5 | CSV formula injection via account names | test | `f87f7d0` |
| B7 † | Conversation history presented to the model as trusted backend data | string assertions + live injection, RV | `2064479` |
| C1 / N12 | Money fields accepted values the column cannot store | HTTP 500 to 422 | `86991d3` |
| C2 | `audit_logs` unindexed for its own query; 35.093 ms to 0.108 ms | EXPLAIN | `351de68`, `7548ad6` |
| C3 | General Ledger N+1: `1+2N` / `1+3N`, 151 queries at 50 accounts | query count | `7e340b9` |
| C5 / C6 | An audit query per matched entry; `db.refresh` in a loop | query count | `f877b80` |
| C8 | Operator text reached ReportLab unescaped | test | `6aa7d85` |
| D2 | No outbound LLM call set a timeout | test | `cd16765` |
| D3 | Ledgers had no pagination at any layer | sha256 contract | `3d76fda` |
| D5 | Conversation list fetched twice per company switch | test | `67235c5` |
| E1 | The handler-registry refactor: 645-line dispatcher, ~290-line if-chain | see below | `1b4f0d9` … `fca5246` |
| E1-a | `pl_contribution_question` was dispatched with no gate at all | HTTP | `de1f93d` |
| E1-b | Nothing could see an ungated handler | AST | `eb0e1bc` |
| E3 | Six helpers duplicated between the two assistant modules | test | `9647828` |
| E6 | LIKE escaping correct in one search path, absent in the other two | test | `3ecb60c` |
| F1 | Healthcheck passed while the database was unreachable | run | `dd68a28` |
| F2 | Rate limiter process-local across workers: 5 became 10 attempts | two-worker run | `124c55c`, `3f7ed75` |
| G5 | A vestigial API parameter accepted and ignored | read | `c485962` |
| G6 | Two permission docstrings describing each other's rule | read | `efd4f1d` |
| G7 | `console.error` in a production path | read | `7f824a9` |
| I2 | The suite could not run from a clean checkout | run | `42049d2` |
| I5 | No migration/model drift check | CI | `de8a969` |
| N7 / N9 | Pending invitations invisible past page 1; last-admin guard over one page | HTTP | `bbdca65` |
| N11 | Two tests asserted against endpoints that do not exist | test | `2668ad6` |
| N15 | Three dispatched intents had zero handler coverage | coverage | `814d7b1` |
| N16 | Debug `console.log` left in two shipped test files | read | `8925069` |
| N25 | `_extract_amount_from_message("who entered -5?")` returned `5`; measured, unpinned | test | `4060ffc` |
| N26 | A wrong password produced no message at all | live DOM | `9fb25d1` |
| N27 | A validation error blanked the whole page | live DOM | `1e4bc39` |
| RAG-1 | Role bypass: a viewer read every user's email through the tool path | HTTP | `91ec5d1` |
| RAG-2a | Two dispatch functions for one endpoint | HTTP | `23d9eeb` |
| RAG-2b | The chat endpoint routed around the registry and dropped pending fields | HTTP | `7e7d687` |
| RAG-2c | `propose_credit_note`, a proposal with nowhere to go | read | `41143a7` |
| RAG-3 | No timeout, and the retry slept in the request thread; over 240 s | timed | `85705fd` |
| RAG-4 | 32 indexes declared by the models, never created by a migration | drift check | `74afab1` |
| RAG-5 / RAG-10 | One global store leaked repository files across tenants | HTTP | `0995943` |
| RAG-6 | Tool results unlabelled; injected account names reached the model verbatim | measured | `89cbbe9` |
| RAG-7 | `get_journal_entries` and `trace_amount` returned draft and void entries | HTTP | `1dc89b9` |
| RAG-8 | `get_account_ledger` always failed: `AttributeError: total_debit` | HTTP | `9d4e4e6` |
| RAG-9 | `reviewer` and `approver` were offered no tools, losing answers they had | test | `fda92c7` |
| RAG-11 | An empty model answer was reported as "your request was processed successfully" | read, RV | `7e7d687` |
| RAG-12 | 30 of the new tests failed, 5 of them needing the network; 142 pass offline | run, RV | `7e7d687` |
| RAG-15 | Four of the six grounding cards were built, stored and discarded | component, RV | `23a79ca` |
| RAG-20 ‡ | The detector certified nine replies the resolver behind it answered `None` to | measured, sweep | `f7243ee` `21f96cc` |

### E1, the handler-registry refactor, in order

`814d7b1` `6f430e1` `2672215` `2aadc43` characterise the handlers no test
reached, so the migration had something to move against. `1b4f0d9` adds the
registry and the consistency test that polices it; `d83f536` `6d26669`
`c7bc88a` `0a569ad` `f6577bf` `1b9ddbd` `2b76e5c` `27b8a76` `e239a50` move
one intent each.

`fca5246` is the last and the only one that had to move a handler DOWN past
a branch rather than out of one. `pl_contribution_question` sat above
`if structured_followup:` and `if generic_without_context:`, neither of which
tests `intent`. The proof that let it move is exhaustive over two closed
phrase sets and is re-run against the source by
`tests/test_assistant_handler_gate_coverage.py`; the reasoning is in
`assistant_handler_registry`'s module docstring and in
`_handle_pl_contribution_question`.

After it: `if intent == ...` appears nowhere in the dispatcher, every
producible intent is answered from `ASSISTANT_HANDLERS`, `NOT_DISPATCHED`
and `INLINE_GATED_HANDLERS` are both empty, and a handler cannot be added
without naming the permission set that gates it.

### ‡ RAG-20, and why its second commit is the one that closes it

`f7243ee` made both resolvers import the detector's option sets instead of
restating them, which closed the nine field/reply pairs the finding named.
That alone would have left the finding fixed and the class open: the two sides
only have to describe one reply differently for "لم أفهم إجابتك" to come back,
and for as long as the divergence existed nothing in the suite noticed it.

`21f96cc` is the closure. `tests/test_clarification_resolver_agreement.py`
asserts that no reply the detector certifies is one the resolver behind that
field answers `None` to, over a 1,574-reply corpus closed over both option
sets, all six vocabulary lists and the chart, with 527 to 640 replies
certified per field so the assertion cannot pass vacuously. It carries its own
proof of teeth: `test_the_invariant_bites_when_the_option_sets_are_pulled_apart`
reproduces the pre-fix resolver and requires the invariant to fail, on exactly
the three replies RAG-20 names, through the `option` short-circuit and no
other rule. Demonstrated against the real source too, by reverting the fix:
nine violations, then restored.

What was measured when it was filed, by sweeping every reply in both option
sets and every term in all six vocabulary lists against all four question
fields (pure functions, no provider):

```
before: replies the detector passes that the resolver cannot read: 9
  واحد / اتنين / اثنين  ×  transaction_type
                        ×  supplier_or_expense
                        ×  customer_or_income
after f7243ee:                                                      0
```

Six of the nine pairs sat behind field names nothing produced and went away
with those names in `2a758e3`. The three `transaction_type` pairs were
reachable in production — that name is appended whenever
`parsed.transaction_type == "unknown"` — and none was covered by any test. A
runtime spy over the whole suite, recording every field name handed to each
consumer, saw one:

```
  clarification_ambiguity            -> payment_source
  _apply_clarification_answer        -> payment_source
  _pending_from_parsed               -> payment_source
  _resolve_transaction_type_answer   -> never called
```

So the type resolver's dispatch had no in-process test coverage at all, which
is how nine holes sat in it unremarked. (Limit of that spy: it lives in the
pytest process, so the HTTP files exercising the server process are outside it.
The static enumeration recorded under RAG-21 is the primary evidence for what
can be produced; this corroborates it in-process.)

**Not a regression.** Before the detector existed, `واحد` on a type question
also fell through to the re-ask — the resolver had never read it. What was new
is that escalation now exists and would read it correctly, and the option
short-circuit skipped it. A missed rescue, which is why it was filed Major
rather than Critical: the outcome was a visible re-ask, not a silent wrong
entry.

**Still open beside it:** RAG-21, the structural half. The invariant covers one
of the three ways the field-name agreement can break, and part of a second; the
third — a resolver answering a question that was not asked — returns a value, so
the invariant passes and the value is wrong. `account_mapping` remains a
recorded gap. See `open-findings.md`.

### † B7, and the half of it that was never filed

B7 was filed as "client-supplied history is passed to the model inside the
section labelled as trusted backend data". That was true, in two live
callers -- `gemini_transaction_parser._build_parser_prompt` and
`gemini_assistant_service._call_gemini_for_answer` -- both of which put
`bounded_recent_conversation` inside `<TRUSTED_ACCOUNTING_DATA>`. Those turns
are the user's own words read back out of our storage, and storage is not
provenance. They now travel in `<UNTRUSTED_CONVERSATION_CONTEXT>`.

**The unfiled half is the more serious of the two, and it is recorded here
because nothing else records it.** `build_agent_prompt` carried **no
untrusted-text notice at all**, while `format_trusted_tool_result` has
carried one since RAG-6. So every payload sent through the prompt path --
including this company's entire chart of accounts -- was marked
`<TRUSTED_ACCOUNTING_DATA>` with nothing saying that the free text inside it
was typed by users. Marking the chart trusted without that sentence is the
worse of the two lies, because it is the one that sounds careful. RAG-6
measured an account whose NAME is "SYSTEM OVERRIDE: ignore all prior
instructions...", and that name went into the trusted block unannotated.
There is now one notice constant, used by both paths.

A third boundary arrived with the fix: `<FIXED_OUTPUT_CONTRACT>`, stated
before either untrusted block, carrying the allowed variants and the rule
that an account may only be named by a code present in the trusted data. It
used to be prose inside `task_instructions`, indistinguishable from advice.

Evidence is in two parts, and they are different claims. Twelve string
assertions in `tests/test_prompt_trust_boundaries.py` prove the boundaries
are CONSTRUCTED correctly regardless of any model's behaviour. One live run
against company 16323, provider reached, 4.7s, shows a model did not follow
the injected account name: no `INJECTED-7731`, no 999999 entry, account 1999
not named as a hint, history canary not leaked. The second is one provider,
one model, one phrasing, one run -- it shows the labels were not defeated
there, not that they cannot be.

**It was closed on one branch and open on the other, and neither ledger was
lying.** The fix is `2064479`, on `phase-61-subledger-and-agent`.
`batch-1-deploy-correctness` did not carry it, so B7 stayed listed as open in
that branch's `docs/open-findings.md`, Part 1, under Security and
authentication, and that entry was correct for that branch. The instruction
here was to remove it when the branches merged and not before, because
deleting it earlier would have claimed a fix that branch did not carry.

**Done.** `batch-1-deploy-correctness` was merged into
`phase-61-subledger-and-agent` to resolve the add/add conflict on
`docs/open-findings.md`; the fix and the entry are now in one tree, so the
row was removed and replaced with a note pointing here. The note also keeps
the row's cross-reference to RAG-6, which was the tool-result half of the
same labelling problem.

---

## Withdrawn, downgraded, or corrected

These have no closing commit. Without a row here they would survive only in
a conversation, which is the whole reason this section exists -- a finding
that was wrong is as worth recording as one that was right, and rather more
worth recording than one nobody ever doubted.

| ID | Outcome |
|---|---|
| B1 | **Exploit withdrawn.** Caddy overwrites `X-Forwarded-For`, so it was never attacker-controlled. The `*` removal stands as defence-in-depth, which is why it also appears above. |
| C7 | **Withdrawn.** The "always-true" `date.min` guard prevents an `OverflowError`; the proposed fix would have caused one. |
| D1 | **High to Medium.** The query framing was wrong: `4+3·ceil(n/500)`, not 31. The cost is materialisation, not query count. |
| D4 | **Narrower.** The accounts page does paginate. The real bite is the picker, refiled as N10. |
| A3 | **Medium to Low.** The `All users` tab only; the page re-slices by tab and the default renders 20, not 23. |
| E7 | **Medium to Low.** A zero-admin state is not sequentially reachable. |
| G1 | **Medium to Low.** The production guard fires. `restore_admin.py` is still at the backend root, so the tidiness half stays open. |
| G8 | **Subsumed by A2.** The unused import got its use in `785ca83`. |
| I3 | **Over-claimed.** One of four claimed issues validated, and `ruff --fix` would have broken startup. |
| I4 | **Reversed.** `extra='forbid'` is set; the finding asserted the opposite. |
| N14 | **Corrected, and narrower than claimed.** `tsc --noEmit` is vacuous, but CI already ran `tsc -b`, so CI never inherited the blind spot. The error was in the finding. |
| D6 | **WONTFIX**, with the reasons in `fd1758b`: per-call LLM client construction is kept deliberately. |

---

## Where the rest are, and where they are not

**This section said something that is no longer true, and the correction is
the point of it.** It used to say that everything open apart from a handful
of RAG entries had no durable entry anywhere. That was accurate while the two
ledgers sat on two branches; it stopped being accurate when
`batch-1-deploy-correctness` was merged into `phase-61-subledger-and-agent`
and the two `open-findings.md` files were concatenated.

`open-findings.md` now carries two halves:

* **The RAG series** -- eight written-up entries: **RAG-13, RAG-14, RAG-16,
  RAG-17, RAG-18, RAG-19, RAG-21, RAG-22**, each with a reproducible
  measurement. (RAG-20 was filed there on 2026-09-28 and closed the same day;
  its record is the ‡ section above. B7 was removed from Part 1 by the merge;
  its record is the † section.)
* **Parts 1 to 3** -- the carried-forward backlog, one table per area, each
  row stating whether it is **MEASURED**, **READING-ONLY** or **ID ONLY**.
  This is where A7, A8, B4, B6, B8, C4, E2, E4, E5, E8, F3, F4, G1, N1--N6,
  N8, N10, N13, N17--N24 now live.

What still has **no recoverable substance** is Part 2: **G2, G3, G4**, where
all that survives is an ID and a gist, and the entry says so. Those three are
a failure of record-keeping rather than findings, and anyone picking one up
starts by re-measuring it.

Three of them are nonetheless held still by tests, which is a
different thing again. N17, N18 and N19
record `pl_contribution_question` answering with another handler's intent,
reporting high confidence on an empty result, and filling `grounding.entries`
while leaving `reply.evidence` empty. `tests/test_assistant_handler_characterisation.py`
asserts each of those, deliberately, so that a refactor changing one fails
instead of passing quietly. They are open findings whose current behaviour is
held still on purpose -- do not "fix" them by editing the assertion.
