"""persist assistant conversations

Revision ID: e8b3d0f5c2a7
Revises: d7a2c9e4b1f6
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e8b3d0f5c2a7"
down_revision = "d7a2c9e4b1f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_assistant_conversations_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assistant_conversations_company_id",
        "assistant_conversations",
        ["company_id"],
    )
    op.create_index(
        "ix_assistant_conversations_user_id",
        "assistant_conversations",
        ["user_id"],
    )
    op.create_index(
        "ix_assistant_conversations_last_message_at",
        "assistant_conversations",
        ["last_message_at"],
    )
    op.create_index(
        "ix_assistant_conversations_owner_company_activity",
        "assistant_conversations",
        ["user_id", "company_id", "last_message_at"],
    )

    op.create_table(
        "assistant_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=2), nullable=False),
        sa.Column("message_type", sa.String(length=30), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("client_message_id", sa.String(length=100), nullable=True),
        sa.Column("in_reply_to_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "language IN ('en', 'ar')", name="ck_assistant_messages_language"
        ),
        sa.CheckConstraint(
            "message_type IN ('text', 'journal_preview', 'report_result', "
            "'clarification', 'error', 'system_notice')",
            name="ck_assistant_messages_type",
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'system_event')",
            name="ck_assistant_messages_role",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["assistant_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["in_reply_to_id"], ["assistant_messages.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id",
            "client_message_id",
            name="uq_assistant_messages_client_message",
        ),
        sa.UniqueConstraint(
            "in_reply_to_id", name="uq_assistant_messages_in_reply_to_id"
        ),
    )
    op.create_index(
        "ix_assistant_messages_conversation_created",
        "assistant_messages",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistant_messages_conversation_created",
        table_name="assistant_messages",
    )
    op.drop_table("assistant_messages")
    op.drop_index(
        "ix_assistant_conversations_owner_company_activity",
        table_name="assistant_conversations",
    )
    op.drop_index(
        "ix_assistant_conversations_last_message_at",
        table_name="assistant_conversations",
    )
    op.drop_index(
        "ix_assistant_conversations_user_id",
        table_name="assistant_conversations",
    )
    op.drop_index(
        "ix_assistant_conversations_company_id",
        table_name="assistant_conversations",
    )
    op.drop_table("assistant_conversations")