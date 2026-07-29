# AI Architecture

## Objective

The accounting assistant should be an application capability, not a Gemini- or
OpenAI-shaped subsystem. External models help interpret or present information;
they do not own accounting truth, permissions, company scope, or mutation
authorization.

The current rules/Gemini/OpenAI provider separation and deterministic fallback
are valuable foundations. The main migration need is to decompose the large
assistant orchestration while preserving its current API and safeguards.

## Provider-neutral model

Application DTOs should describe:

- User message and language.
- Trusted company and actor context.
- Conversation context with explicit bounds.
- Intent decision and extracted accounting entities.
- Grounded accounting facts and their sources.
- Confidence and warnings.
- Proposed action requiring confirmation.
- Final reply independent of provider SDK response types.

Provider names may be included as diagnostic metadata, but must not determine
the application workflow or ordinary frontend layout.

## Application ports

Suggested ports include:

```text
JournalSuggestionProvider
IntentClassifier
AccountingAnswerGenerator
ConversationRepository
AccountingGroundingReader
AssistantAuditPort
```

Ports use typed, provider-neutral requests and results. They do not expose
Gemini/OpenAI clients, response objects, token structures, or SDK exceptions.

## Application use cases

Focused use cases should replace one monolithic dispatcher over time:

- Classify an assistant request.
- Ground a report or ledger question.
- Answer a grounded accounting question.
- Propose a journal action.
- Continue or summarize conversation context.
- Confirm an assistant-proposed action.

Application responsibilities include:

- Actor permissions and company isolation.
- Selection of trusted accounting data sources.
- Fiscal and journal eligibility.
- Data minimization before provider calls.
- Decision to use deterministic or external capability.
- Confirmation-token/action validation.
- Required audit event coordination.

## Infrastructure adapters

Infrastructure implementations include:

- Deterministic rules adapter.
- Gemini adapter.
- OpenAI adapter.
- Provider-specific intent classifier.
- Provider-specific answer generator.

Adapters own:

- SDK initialization and configuration.
- Prompt templates and system instructions.
- Separation of trusted instructions from user text.
- Provider request construction.
- JSON parsing and schema validation.
- Timeouts, retry policy, and provider-specific failures.
- Mapping provider output into application DTOs.

Prompt construction belongs with provider infrastructure because prompt syntax
and supported contracts vary by provider. Accounting facts supplied to those
prompts are selected by application grounding services.

## Fallback behavior

Fallback policy should be explicit:

1. The application requests a capability.
2. The selected adapter either returns a validated result or a typed unavailable
   result/error.
3. An application-level policy selects deterministic fallback when appropriate.
4. The final response records its confidence, warnings, and grounding source.

Avoid hidden fallback at multiple nested levels. A single observable policy
makes tests and production diagnostics more reliable.

## Grounding and permissions

External providers must receive only data already authorized for the actor and
selected company. The application layer must:

- Resolve company context from trusted authentication state, not model output.
- Check report, journal, audit, and user-management permissions.
- Retrieve facts through authorized readers.
- Bound history and remove unrelated or sensitive context.
- Refuse cross-company requests.
- Preserve deterministic calculations as the source of accounting truth.

Models may explain validated report results; they must not invent or replace
ledger calculations.

## Mutation safety

AI output is advisory. A proposed mutation must:

- Be represented as a typed action draft.
- Be validated against current company, permissions, accounts, fiscal periods,
  and journal rules.
- Be shown to the user before execution.
- Require explicit confirmation.
- Be revalidated at confirmation time.
- Execute through the same application use case as a non-AI action where
  possible.
- Commit atomically with its required audit record.

Provider output must never directly call a repository or commit a transaction.

## Frontend boundary

Frontend assistant components should consume a provider-neutral contract:

- Message role and content.
- Grounding/source indicators.
- Confidence or warning.
- Suggested accounting action.
- Confirmation state.
- Conversation metadata.

The UI may retain the product’s existing assistant name for compatibility, but
provider identity should not dominate styling or component structure. The same
message list, composer, history, and accounting action card should work with
rules, Gemini, OpenAI, or future providers.

## Incremental decomposition

1. Characterize current intent, fallback, grounding, bilingual, and confirmation
   behavior.
2. Define provider-neutral DTOs and ports around the existing dispatcher.
3. Wrap the current service behind a compatibility facade.
4. Extract provider transport and parsing.
5. Extract grounding readers and permission orchestration.
6. Extract individual use cases.
7. Thin `ai_routes.py` only after the use cases are stable.
8. Remove legacy branches after parity is demonstrated.

High-risk safeguards—prompt-injection defense, company isolation, grounding,
deterministic fallback, explicit confirmation, and audit atomicity—must not
weaken during decomposition.
