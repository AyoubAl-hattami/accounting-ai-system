# Phase 0 Behavioral Baseline

This directory records the behavior that must remain stable while the Accounting
AI System moves incrementally toward the architecture described in
[`docs/architecture`](../architecture/README.md).

Phase 0 is observational. It does not change product behavior, source code,
database schema, API contracts, tests, or deployment configuration. The
documents identify existing contracts, evidence, verification commands, manual
checks, and high-risk regression areas.

## How to use this baseline

Before a refactor:

1. Identify the affected risks and contracts in these documents.
2. Record the relevant command results and representative manual observations.
3. Keep the refactor narrow and avoid unrelated behavior changes.

After the refactor:

1. Run the same authorized commands in the same environment.
2. Compare API paths, payloads, status codes, accounting results, permissions,
   audit records, and UI workflows.
3. Investigate every difference; do not classify it as an architectural change
   unless a product change was separately approved.
4. Update this baseline only when an intentional contract change is approved.

The baseline describes expected behavior inferred from current source and tests.
The commands were not executed while creating these documents, so Phase 0 is not
complete until a clean reference run has been recorded.

## Baseline documents

- [Verification commands](verification-commands.md)
- [API contract baseline](api-contract-baseline.md)
- [Accounting domain baseline](accounting-domain-baseline.md)
- [RBAC and security baseline](rbac-and-security-baseline.md)
- [Transaction and audit baseline](transaction-and-audit-baseline.md)
- [AI baseline](ai-baseline.md)
- [Frontend baseline](frontend-baseline.md)
- [Regression risk map](regression-risk-map.md)

## Compatibility boundary

Future architecture work must preserve, unless separately approved:

- API paths, payload fields, response fields, pagination, status codes, and
  error behavior.
- PostgreSQL schema, SQLAlchemy mappings, and Alembic history.
- Journal lifecycle, fiscal enforcement, accounting calculations, and reports.
- Authentication, RBAC, platform privileges, and company isolation.
- Required audit-record atomicity.
- AI grounding, fallback, validation, and confirmation safety.
- Frontend routes, workflows, light/dark behavior, translations, and Arabic/RTL.
