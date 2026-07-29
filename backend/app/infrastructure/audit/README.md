# Audit Infrastructure

Purpose: persist required audit events and implement audit query ports.

May later contain SQLAlchemy audit writers/readers and redaction adapters. It
must not independently commit business operations, contain HTTP policy, or
record secrets.

Status: scaffolding only. Current audit implementation remains under
`backend/app/modules/accounting`.
