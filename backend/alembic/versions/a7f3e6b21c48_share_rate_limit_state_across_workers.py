"""share rate limit state across workers

Revision ID: a7f3e6b21c48
Revises: d4e9a1c73b62

The rate limiter kept its counters in a module-level dict, so uvicorn's two
workers each had their own.  Measured against the configured limit of 5 failed
logins per minute, two workers allowed 10, and a 429 did not end the attempt --
the next request could land on the other worker and be answered 401.

This table is the shared counter.  One row per attempt, keyed by the string
make_rate_limit_key already builds.

Not registered against any tenant and carrying no foreign keys on purpose: an
attempt is recorded before anyone is authenticated.

Two indexes for the two access paths -- counting one bucket inside one window,
and sweeping every bucket older than the longest window.  Both are created with
the table rather than concurrently: the table is empty at this point, so there
is nothing to lock.
"""

from alembic import op
import sqlalchemy as sa


revision = "a7f3e6b21c48"
down_revision = "d4e9a1c73b62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("bucket_key", sa.String(length=255), nullable=False),
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rate_limit_attempts_id", "rate_limit_attempts", ["id"]
    )
    op.create_index(
        "ix_rate_limit_attempts_bucket_time",
        "rate_limit_attempts",
        ["bucket_key", "attempted_at"],
    )
    op.create_index(
        "ix_rate_limit_attempts_attempted_at",
        "rate_limit_attempts",
        ["attempted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_rate_limit_attempts_attempted_at", table_name="rate_limit_attempts")
    op.drop_index("ix_rate_limit_attempts_bucket_time", table_name="rate_limit_attempts")
    op.drop_index("ix_rate_limit_attempts_id", table_name="rate_limit_attempts")
    op.drop_table("rate_limit_attempts")
