# Assistant Intent Orchestrator

Phase 1 introduces a provider-neutral Natural Language Understanding layer between the assistant request and the existing accounting handlers. It classifies and extracts information only. It does not retrieve accounting data, authorize users, calculate reports, or mutate journals.

## Processing precedence

The orchestrator applies this fixed order:

1. Prompt-disclosure refusal.
2. Prompt-injection and cross-company refusal.
3. Fabricated or unsupported financial-estimate refusal.
4. Deterministic identity, capability, greeting, and journal-boundary intents.
5. Confirmation or cancellation of an active pending draft.
6. Validated same-conversation follow-up context.
7. High-confidence deterministic accounting intents.
8. Optional semantic classification.
9. Existing legacy classification.
10. One focused safe clarification.

Security decisions are deterministic and occur before semantic classification. A semantic provider cannot replace or override them.

## Intent catalogue

The canonical catalogue is defined by the strict `AssistantIntent` type and `INTENT_CATALOGUE`. It covers general assistance, security boundaries, Profit and Loss, Balance Sheet, Trial Balance, Account Ledger, General Ledger, financial explanations, journal draft workflow, journal questions and tracing, accounts, audits, and company-user questions. New intents must represent an already supported product operation or be paired with a separately reviewed backend implementation.

Each decision contains an allowlisted `target_handler`. Providers cannot return arbitrary function names, and the orchestrator never invokes a handler itself.

## Entity schema

`AccountingIntentEntities` supports account name/reference and normalized comparison text, account code, Decimal-safe amount, currency, transaction type, payment source, counterparty, description, report and period fields, dates, journal reference, requested metric, and requested action.

User-provided account names are preserved exactly. A separate normalized value may be used for comparison. Generic placeholders such as `account`, `the account`, `this account`, and `الحساب` do not identify an account unless validated same-conversation grounding resolves the reference. Missing amounts or payment sources remain missing; the NLU layer does not invent them.

## Confidence and clarification

Confidence is restricted to `high`, `medium`, or `low`. High-confidence deterministic routes bypass semantic classification. Valid medium/high semantic decisions may select only a compatible allowlisted handler. Low confidence, invalid JSON, schema errors, unknown intents, incompatible handlers, or missing required fields fall through to legacy behavior or a focused clarification.

Clarifications ask for one useful missing item at a time. For example, a payment with an amount but no source asks whether it was paid from bank or cash through the existing transaction workflow. A ledger request with only “the account” asks for the account name or code.

## Semantic provider boundary

`SemanticIntentClassifier` is the provider-neutral interface for a future Gemini or OpenAI adapter. It receives only:

- the latest untrusted message;
- latest-message language;
- a bounded recent conversation summary;
- the allowed intent catalogue;
- backend-derived role capability identifiers;
- the current pending-context type.

Its result is strict JSON validated by Pydantic. User and conversation text are delimited as untrusted data in the provider content payload and never interpolated into immutable system instructions. The classifier cannot calculate totals, retrieve company data, grant permission, invent account IDs, post journals, or select an arbitrary backend function.

Full prompts, conversations, raw provider responses, secrets, and tokens must not be logged. Safe diagnostics may record the selected intent, confidence, source, and validation-failure category.

## Conversation-context safety

Follow-up context is usable only when the authenticated service has established the same user, company, owned conversation, compatible validated grounding, and an active non-cancelled pending state where applicable. Context does not come from conversation titles and does not cross users, companies, or conversations. Malformed, unavailable, expired, or cancelled context is ignored.

## Backend authorization boundary

The decision object describes a request; it grants no access. The assistant service continues to enforce company scope and role capabilities before calling existing trusted handlers. Report application queries remain authoritative for totals, account and ledger application seams for account data, and journal use cases plus repository policy for lifecycle operations. Existing Decimal arithmetic, fiscal-period checks, account validation, idempotency, grounding validation, and conversation ownership remain unchanged.

## Adding an intent safely

1. Confirm that an authoritative backend handler already supports the operation.
2. Add the intent and any required entity fields to the strict schema.
3. Add an explicit intent-to-handler allowlist entry.
4. Define required fields and a focused clarification path.
5. Place security-sensitive deterministic detection before semantic classification.
6. Add Arabic, English, mixed-language, role, validation, and context-isolation tests.
7. Keep authorization, calculations, and mutations in the existing backend service.
