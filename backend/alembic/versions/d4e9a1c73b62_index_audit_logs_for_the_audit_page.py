"""index audit_logs for the audit page and the entity drill-down

Revision ID: d4e9a1c73b62
Revises: e2a7f6c1d904

audit_logs carried only a primary key and a single-column index on
company_id.  The audit page runs

    WHERE company_id = ? [AND entity_type/entity_id/action]
    ORDER BY created_at DESC OFFSET ? LIMIT ?

so PostgreSQL read every row for the tenant and then sorted them to return
a hundred.  At 24,922 rows for one company inside a 500,000-row table that
was a 35 ms top-N heapsort touching 6,177 buffers, for page one.

Two indexes, matching the two access paths:

  ix_audit_logs_company_created  the list, in recency order
  ix_audit_logs_company_entity   the entity drill-down, used by the audit
                                 page's entity_type/entity_id filter and by
                                 the assistant's batched actor lookup

CONCURRENTLY, deliberately.  A plain CREATE INDEX takes a SHARE lock, which
blocks INSERT for the duration -- and audit_logs is written on every login,
every failed login and every mutation in the product, so an exclusive build
on a production-sized table would stall authentication, not just the audit
page.  CONCURRENTLY trades a slower build for leaving writers alone.

CONCURRENTLY cannot run inside a transaction block, and env.py wraps
run_migrations() in context.begin_transaction().  op.get_context()
.autocommit_block() commits the surrounding transaction, runs its body
outside one, and opens a fresh transaction afterwards, which is the
supported way to do this and leaves the rest of the migration chain
untouched.

One consequence worth knowing before running this against production: an
interrupted CONCURRENTLY build leaves an INVALID index behind rather than
rolling back.  It is not used by the planner and is harmless, but it must
be dropped and rebuilt.  Check with:

    SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;
"""

from alembic import op


revision = "d4e9a1c73b62"
down_revision = "e2a7f6c1d904"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_audit_logs_company_created "
            "ON audit_logs (company_id, created_at DESC)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_audit_logs_company_entity "
            "ON audit_logs (company_id, entity_type, entity_id, created_at DESC)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_audit_logs_company_entity")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_audit_logs_company_created")
