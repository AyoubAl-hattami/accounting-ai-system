"""ensure one reversal per original journal entry

Revision ID: c4f7a1d2e9b0
Revises: 953915c692cb
"""
from alembic import op

revision = "c4f7a1d2e9b0"
down_revision = "953915c692cb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_journal_entries_reversal_of_id",
        "journal_entries",
        ["reversal_of_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_journal_entries_reversal_of_id",
        "journal_entries",
        type_="unique",
    )