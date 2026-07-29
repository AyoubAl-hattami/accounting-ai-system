# AI Baseline

## Components

Backend AI code currently includes:

- `services/ai_providers/base.py`
- `services/ai_providers/rules_provider.py`
- `services/ai_providers/openai_provider.py`
- `services/ai_providers/gemini_provider.py`
- `services/ai_providers/llm_placeholder_provider.py`
- `services/ai_provider_factory.py`
- `services/ai_suggestion_service.py`
- `services/assistant_intent_orchestrator.py`
- `services/gemini_agent_contract.py`
- `services/gemini_assistant_service.py`
- `services/gemini_transaction_parser.py`
- `routes/ai_routes.py`
- `routes/assistant_conversation_routes.py`

Frontend AI code is primarily under `frontend/src/features/ai/` and journal
assistant components under `frontend/src/features/journals/assistant/`.

## Rules provider

- The rules provider is deterministic and safe without an external service.
- It is the default journal suggestion provider.
- It resolves recognized accounting descriptions against the supplied company
  accounts.
- Unknown, tied, or materially unresolved inputs must not invent confident
  account selections.
- Confidence/source/warning behavior remains stable.

Evidence: `test_ai_provider_factory.py` and direct rules tests in
`test_gemini_assistant.py`.

## OpenAI provider

- Selected through configuration and the provider factory.
- Uses the current prompt/contract and validates returned JSON.
- Account IDs must exist in the supplied authorized account list.
- Amount and confidence values are validated and normalized.
- Missing configuration, invalid JSON/output, and provider exceptions fall back
  to rules.
- Provider SDK errors do not become unvalidated business output.

Evidence: OpenAI selection, valid output, invalid account, invalid JSON,
exception, helper validation, and status tests in
`test_ai_provider_factory.py`.

## Gemini provider

Gemini follows the same baseline:

- Configuration-driven selection.
- Separated trusted instructions and bounded provider data.
- JSON/output validation.
- Account, amount, and confidence validation.
- Rules fallback for missing key, invalid output, or provider failure.
- Stable source/warning metadata indicating direct versus fallback behavior.

Evidence: Gemini provider tests in `test_ai_provider_factory.py`.

## Provider factory and status

`ai_provider_factory.py` recognizes:

- `rules`
- `llm_placeholder`
- `openai`
- `gemini`

Unknown configuration or initialization failure resolves to rules. The
`GET /ai/status` response retains its current provider, enabled/fallback, source,
and message semantics. Provider status is informational; selecting a provider
must not change accounting authorization or mutation rules.

## Journal suggestions

`POST /ai/journal-suggestions`:

- Requires the current authentication/company context.
- Supplies only company-authorized accounts to the provider.
- Returns the current suggestion contract, including confidence, source, and
  warning fields.
- Does not itself post an accounting transaction.
- Invalid external output is sanitized or replaced by deterministic fallback.

## Global/Gemini assistant

`POST /ai/gemini-assistant`:

- Accepts English and Arabic requests.
- Returns the current structured assistant reply.
- Handles accounting report, journal, audit, user, explanation, trace, and
  action-draft intents according to current permissions.
- Uses deterministic behavior when Gemini is unavailable.
- Refuses fabrication and sensitive prompt/secret disclosure.
- Grounds report answers in system accounting data.
- Returns clarification or unavailable responses rather than invented facts.
- Preview/action proposal does not create a journal entry.

Evidence: `test_gemini_assistant.py`,
`test_gemini_assistant_explain.py`, `test_gemini_assistant_profit.py`,
`test_assistant_intent_orchestrator.py`, and
`test_semantic_transaction.py`.

## Confirmation before mutation

`POST /ai/gemini-assistant/confirm-action` is the explicit mutation boundary:

- The proposed action is revalidated.
- Actor permission and company scope are rechecked.
- Account ownership and fiscal eligibility are checked.
- Viewers cannot confirm.
- Invalid or unavailable fiscal periods return the current structured error.
- Failed confirmation creates no entry.
- A successful action creates the current journal draft/result and audit event.
- Current date restrictions remain in force.

Evidence includes confirmation, audit, fiscal-error, viewer, preview, failure,
and date tests in `test_gemini_assistant.py`.

## Grounding and isolation

- Model output does not establish company identity or permission.
- Cross-company facts must never enter prompts or replies.
- Reports and ledgers remain the source of authoritative totals.
- Draft entries remain excluded from official reports.
- The assistant must not reveal secrets, system prompts, provider keys, raw
  tokens, or unrelated conversation data.
- Conversation access remains scoped to its owner/company rules.

## Frontend baseline

- The global assistant is available through `GlobalGeminiAssistant.tsx`.
- `GeminiAssistantPanel.tsx` presents messages, history, input, and suggested
  accounting actions.
- The journal assistant remains available in the journal workflow.
- Suggested mutations remain visibly confirmable/cancellable.
- Provider identity must not bypass or alter frontend permission visibility.
- English and Arabic direction must remain usable.

## Refactor invariants

Provider decomposition must preserve:

- Rules fallback availability.
- Output validation.
- Confidence/source meaning.
- Grounding and company isolation.
- Permission checks.
- Prompt-injection and fabrication defenses.
- Explicit confirmation and revalidation.
- Atomic mutation/audit behavior.
- Existing API payloads and frontend workflows.
