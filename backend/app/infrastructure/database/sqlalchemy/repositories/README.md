# SQLAlchemy Repositories

Purpose: implement application repository ports with SQLAlchemy.

May later contain focused account, journal, fiscal, company, invitation, user,
audit, conversation, and report-reader adapters. It must not expose unrestricted
query builders, commit independently, or implement HTTP behavior.

Status: scaffolding only. Existing service queries remain under
`backend/app/modules/accounting`.
