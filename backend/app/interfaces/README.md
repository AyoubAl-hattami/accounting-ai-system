# Interface Layer

Purpose: expose application capabilities through delivery mechanisms.

May later contain API and other interface adapters. It must not contain
accounting invariants, concrete persistence queries, AI SDK calls, or transaction
commits.

Status: scaffolding only. Current routes and schemas remain under
`backend/app/modules/accounting`.
