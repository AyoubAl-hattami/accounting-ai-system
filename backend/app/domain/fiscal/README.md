# Fiscal Domain

Purpose: define fiscal-year and fiscal-period business policy.

May later contain date-range, open-period, overlap, and eligibility rules. It
must not contain SQLAlchemy queries, FastAPI errors, migrations, or transaction
control.

Status: scaffolding only. Current fiscal behavior remains in
`backend/app/modules/accounting`.
