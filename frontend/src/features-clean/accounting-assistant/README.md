# Accounting Assistant Feature

Purpose: eventually encapsulate provider-neutral assistant conversation actions.

May later contain conversation state, messages, composer, history, grounding,
and explicit action confirmation. It must not bypass permissions, directly
commit mutations, or couple UI structure to Gemini/OpenAI.

Status: scaffolding only. Existing AI components remain in
`frontend/src/features/ai`.
