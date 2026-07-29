# Infrastructure Layer

Purpose: implement technical adapters required by application ports.

May later contain SQLAlchemy persistence, AI providers, security adapters, audit
persistence, and exporters. It must not own endpoint policy, company
authorization decisions, or accounting invariants.

Status: scaffolding only. Current implementations remain under
`backend/app/modules/accounting` and `backend/app/core`.
