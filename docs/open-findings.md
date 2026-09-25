# Open findings

Findings that have been measured and not yet fixed.

Fixed findings are not listed here: their record is the commit that closed
them, which carries the ID in its subject (`[RAG-1]`, `[D2]`, `[A9]`, and so
on). This file exists for the other kind -- the ones found while looking for
something else, which otherwise survive only in a conversation.

Note that the **F-001 to F-025** index in
`audit-report/Accounting_AI_System_Technical_Audit.md` is a separate
numbering from the IDs used here, and no cross-walk between the two exists.
`F2` here is the process-local rate limiter; `F-002` there is audit
atomicity. They collide by accident. An `F-00x` that looks accounted for here
has not been looked at under that number.

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
| **B7** | Client-supplied conversation history is passed to the model inside the section labelled as trusted backend data, so a user can write text that the prompt presents as system-provided. | **READING-ONLY.** The labelling is visible in the prompt builder; whether a model actually follows planted history was never measured. RAG-6 closed the tool-result half of this; the history half is this entry. |
| **B8** | No dependency vulnerability scanning of any kind. | **MEASURED**, re-run 2026-09-26: no `dependabot.yml`, and no `pip-audit`, `safety`, `trivy` or `snyk` anywhere under `.github/`. |

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
