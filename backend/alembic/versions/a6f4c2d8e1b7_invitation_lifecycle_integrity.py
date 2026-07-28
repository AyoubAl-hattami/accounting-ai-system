"""Invitation lifecycle integrity and pending uniqueness.

Revision ID: a6f4c2d8e1b7
Revises: f9c4e1a6d3b8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6f4c2d8e1b7"
down_revision: Union[str, Sequence[str], None] = "f9c4e1a6d3b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "company_user_invitations",
        sa.Column("normalized_email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "company_user_invitations",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "company_user_invitations",
        sa.Column("cancelled_by_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_company_user_invitations_cancelled_by_user_id",
        "company_user_invitations",
        "users",
        ["cancelled_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE company_user_invitations
        SET normalized_email = lower(btrim(email))
        WHERE normalized_email IS NULL
        """
    )
    op.execute(
        """
        UPDATE company_user_invitations
        SET cancelled_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
        WHERE accepted_at IS NULL
          AND cancelled_at IS NULL
          AND expires_at <= CURRENT_TIMESTAMP
        """
    )
    op.execute(
        """
        WITH ranked_live AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY company_id, normalized_email
                       ORDER BY expires_at DESC, created_at DESC, id DESC
                   ) AS live_rank
            FROM company_user_invitations
            WHERE accepted_at IS NULL
              AND cancelled_at IS NULL
        )
        UPDATE company_user_invitations AS invitation
        SET cancelled_at = CURRENT_TIMESTAMP
        FROM ranked_live
        WHERE invitation.id = ranked_live.id
          AND ranked_live.live_rank > 1
        """
    )

    op.alter_column(
        "company_user_invitations",
        "normalized_email",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.create_check_constraint(
        "ck_company_user_invitation_single_terminal_state",
        "company_user_invitations",
        "NOT (accepted_at IS NOT NULL AND cancelled_at IS NOT NULL)",
    )
    op.create_index(
        "ix_company_user_invitations_company_normalized_email",
        "company_user_invitations",
        ["company_id", "normalized_email"],
        unique=False,
    )
    op.create_index(
        "uq_company_user_invitations_live",
        "company_user_invitations",
        ["company_id", "normalized_email"],
        unique=True,
        postgresql_where=sa.text(
            "accepted_at IS NULL AND cancelled_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_company_user_invitations_live",
        table_name="company_user_invitations",
    )
    op.drop_index(
        "ix_company_user_invitations_company_normalized_email",
        table_name="company_user_invitations",
    )
    op.drop_constraint(
        "ck_company_user_invitation_single_terminal_state",
        "company_user_invitations",
        type_="check",
    )
    op.drop_constraint(
        "fk_company_user_invitations_cancelled_by_user_id",
        "company_user_invitations",
        type_="foreignkey",
    )
    op.drop_column("company_user_invitations", "cancelled_by_user_id")
    op.drop_column("company_user_invitations", "cancelled_at")
    op.drop_column("company_user_invitations", "normalized_email")
