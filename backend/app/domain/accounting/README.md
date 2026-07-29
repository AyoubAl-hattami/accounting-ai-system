# Accounting Domain

Purpose: define core accounting invariants independently of persistence and APIs.

May later contain journal balance, debit/credit, posting, reversal, void,
opening-balance, and account-classification policies. It must not contain routes,
ORM queries, report presentation, audit commits, or AI SDK logic.

Status: scaffolding only. Current accounting behavior remains in
`backend/app/modules/accounting` until a verified migration.
