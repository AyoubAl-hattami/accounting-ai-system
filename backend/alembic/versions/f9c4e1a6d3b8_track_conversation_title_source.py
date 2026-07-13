"""track assistant conversation title provenance

Revision ID: f9c4e1a6d3b8
Revises: e8b3d0f5c2a7
"""

from alembic import op
import sqlalchemy as sa

revision = "f9c4e1a6d3b8"
down_revision = "e8b3d0f5c2a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assistant_conversations",
        sa.Column(
            "title_source",
            sa.String(length=20),
            server_default="auto",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_assistant_conversations_title_source",
        "assistant_conversations",
        "title_source IN ('fallback', 'greeting', 'auto', 'manual')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_assistant_conversations_title_source",
        "assistant_conversations",
        type_="check",
    )
    op.drop_column("assistant_conversations", "title_source")