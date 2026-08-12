"""invalidate access tokens after credential changes

Revision ID: e2a7f6c1d904
Revises: c9d4b7e2f813
"""

from alembic import op
import sqlalchemy as sa


revision = "e2a7f6c1d904"
down_revision = "c9d4b7e2f813"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
