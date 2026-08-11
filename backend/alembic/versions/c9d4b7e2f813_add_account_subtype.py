"""classify accounts as bank / cash / e-wallet without renaming them

Revision ID: c9d4b7e2f813
Revises: b2e5c8f14a37
"""

from alembic import op
import sqlalchemy as sa

revision = "c9d4b7e2f813"
down_revision = "b2e5c8f14a37"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable on purpose: existing charts keep working untouched, and reports
    # never read this column — they classify by account_type alone.
    op.add_column(
        "accounts",
        sa.Column("account_subtype", sa.String(length=30), nullable=True),
    )
    op.create_check_constraint(
        "ck_accounts_account_subtype",
        "accounts",
        "account_subtype IS NULL OR account_subtype IN ("
        "'bank', 'cash', 'e_wallet', 'receivable', 'payable', "
        "'revenue', 'expense', 'other')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_accounts_account_subtype", "accounts", type_="check")
    op.drop_column("accounts", "account_subtype")
