# SQLAlchemy Repositories

Purpose: implement application repository ports with SQLAlchemy.

Contains focused account, fiscal, journal, and report-reader adapters. These
adapters may use SQLAlchemy models and sessions, but must not implement HTTP
behavior or commit independently. The report repository remains read-only;
mutation repositories may flush only at their established mutation seams.

Status: active for the migrated accounting slices. Static repository rules are
enforced by `backend/tests/test_architecture_guards.py`.
