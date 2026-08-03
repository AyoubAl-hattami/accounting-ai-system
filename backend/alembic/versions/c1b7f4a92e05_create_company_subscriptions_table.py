"""create company subscriptions table

Revision ID: c1b7f4a92e05
Revises: a6f4c2d8e1b7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1b7f4a92e05"
down_revision: Union[str, Sequence[str], None] = "a6f4c2d8e1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("plan_code", sa.String(length=50), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspension_reason", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('trial', 'active', 'past_due', 'suspended', 'cancelled')",
            name="ck_company_subscriptions_status",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_company_subscriptions_company"),
    )
    op.create_index(
        op.f("ix_company_subscriptions_id"),
        "company_subscriptions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_subscriptions_company_id"),
        "company_subscriptions",
        ["company_id"],
        unique=False,
    )

    # Companies that predate subscription management must keep working, so they
    # are backfilled as active with no expiry until a platform admin sets one.
    op.execute(
        """
        INSERT INTO company_subscriptions (company_id, status, created_at, updated_at)
        SELECT id, 'active', now(), now() FROM companies
        """
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_company_subscriptions_company_id"),
        table_name="company_subscriptions",
    )
    op.drop_index(
        op.f("ix_company_subscriptions_id"),
        table_name="company_subscriptions",
    )
    op.drop_table("company_subscriptions")
