# Audit Application

Purpose: coordinate required audit events with business use cases.

May later contain audit ports, redacted DTOs, and query use cases. It must not
contain concrete database writes, HTTP request parsing, provider telemetry, or
secrets.

Status: scaffolding only. Current audit behavior remains in
`backend/app/modules/accounting`.
