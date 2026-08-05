"""require a password change after a temporary credential handover

Revision ID: b2e5c8f14a37
Revises: c1b7f4a92e05
"""

from alembic import op
import sqlalchemy as sa

revision = "b2e5c8f14a37"
down_revision = "c1b7f4a92e05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing accounts chose their own passwords, so none of them is holding a
    # handed-over credential and the backfill is false for every row.
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
