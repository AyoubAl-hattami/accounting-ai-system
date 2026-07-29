# Audit Domain

Purpose: describe required business audit events without persistence concerns.

May later contain audit event types and redaction invariants. It must not contain
database writes, commits, HTTP request objects, telemetry adapters, or secrets.

Status: scaffolding only. Current audit behavior remains in
`backend/app/modules/accounting`.
