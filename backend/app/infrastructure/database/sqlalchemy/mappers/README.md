# SQLAlchemy Mappers

Purpose: translate between persistence records and domain/application objects
where separate representations are justified.

May later contain explicit mapping functions. It must not contain accounting
policy, database commits, API serialization, or speculative duplicate entities.

Status: scaffolding only. Current ORM objects remain in use under
`backend/app/modules/accounting`.
