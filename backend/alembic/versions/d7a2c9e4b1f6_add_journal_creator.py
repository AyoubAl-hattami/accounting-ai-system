'''add journal creator attribution

Revision ID: d7a2c9e4b1f6
Revises: c4f7a1d2e9b0
'''
from alembic import op
import sqlalchemy as sa

revision = 'd7a2c9e4b1f6'
down_revision = 'c4f7a1d2e9b0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('journal_entries', sa.Column('created_by_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_journal_entries_created_by_user_id', 'journal_entries', 'users', ['created_by_user_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_journal_entries_created_by_user_id', 'journal_entries', ['created_by_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_journal_entries_created_by_user_id', table_name='journal_entries')
    op.drop_constraint('fk_journal_entries_created_by_user_id', 'journal_entries', type_='foreignkey')
    op.drop_column('journal_entries', 'created_by_user_id')
