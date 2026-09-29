"""create_subledger_indexes

The three subledger migrations create the tables and their constraints but
none of their indexes, while the models declare 32 of them -- so the CI drift
check from [I5] fails: autogenerate wants to create every one.

Both halves of that disagreement were checked before choosing a side. The
declarations are deliberate and match what every older table does: accounts,
journal_entries and audit_logs each carry the same index=True on the primary
key and on their foreign keys, and each has a migration that creates them
(d17a284486bd creates ix_accounts_id and ix_accounts_company_id, for one).
The index on `id` is redundant with the primary key's own unique index on
PostgreSQL, but making these tables the exception would be a separate
decision about every table, not a fix for this one.

So the migration is what was missing, and this is it. The statements are
rendered from what autogenerate asked for against a database at
d9e2f1a8b7c6, not typed from the models by hand.

Written as a new revision rather than folded into the three, because those
are already applied to working databases.

Revision ID: f3b7c40e91da
Revises: d9e2f1a8b7c6
Create Date: 2026-09-23 09:40:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f3b7c40e91da"
down_revision: Union[str, Sequence[str], None] = "d9e2f1a8b7c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f('ix_credit_note_allocations_company'), 'credit_note_allocations', ['company_id'], unique=False)
    op.create_index(op.f('ix_credit_note_allocations_id'), 'credit_note_allocations', ['id'], unique=False)
    op.create_index(op.f('ix_credit_note_allocations_invoice'), 'credit_note_allocations', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_credit_note_lines_id'), 'credit_note_lines', ['id'], unique=False)
    op.create_index(op.f('ix_credit_notes_created_by_user_id'), 'credit_notes', ['created_by_user_id'], unique=False)
    op.create_index(op.f('ix_credit_notes_id'), 'credit_notes', ['id'], unique=False)
    op.create_index(op.f('ix_credit_notes_partner_id'), 'credit_notes', ['partner_id'], unique=False)
    op.create_index(op.f('ix_invoice_lines_account_id'), 'invoice_lines', ['account_id'], unique=False)
    op.create_index(op.f('ix_invoice_lines_id'), 'invoice_lines', ['id'], unique=False)
    op.create_index(op.f('ix_invoice_lines_invoice_id'), 'invoice_lines', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_invoices_company_id'), 'invoices', ['company_id'], unique=False)
    op.create_index(op.f('ix_invoices_created_by_user_id'), 'invoices', ['created_by_user_id'], unique=False)
    op.create_index(op.f('ix_invoices_id'), 'invoices', ['id'], unique=False)
    op.create_index(op.f('ix_invoices_journal_entry_id'), 'invoices', ['journal_entry_id'], unique=False)
    op.create_index(op.f('ix_invoices_partner_id'), 'invoices', ['partner_id'], unique=False)
    op.create_index(op.f('ix_partners_id'), 'partners', ['id'], unique=False)
    op.create_index(op.f('ix_partners_payable_account_id'), 'partners', ['payable_account_id'], unique=False)
    op.create_index(op.f('ix_partners_receivable_account_id'), 'partners', ['receivable_account_id'], unique=False)
    op.create_index(op.f('ix_payment_allocations_company'), 'payment_allocations', ['company_id'], unique=False)
    op.create_index(op.f('ix_payment_allocations_id'), 'payment_allocations', ['id'], unique=False)
    op.create_index(op.f('ix_payment_allocations_invoice'), 'payment_allocations', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_payments_bank_or_cash_account_id'), 'payments', ['bank_or_cash_account_id'], unique=False)
    op.create_index(op.f('ix_payments_created_by_user_id'), 'payments', ['created_by_user_id'], unique=False)
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    op.create_index(op.f('ix_payments_partner_id'), 'payments', ['partner_id'], unique=False)
    op.create_index(op.f('ix_payments_receivable_or_payable_account_id'), 'payments', ['receivable_or_payable_account_id'], unique=False)
    op.create_index(op.f('ix_refunds_bank_or_cash_account_id'), 'refunds', ['bank_or_cash_account_id'], unique=False)
    op.create_index(op.f('ix_refunds_created_by_user_id'), 'refunds', ['created_by_user_id'], unique=False)
    op.create_index(op.f('ix_refunds_credit_note_id'), 'refunds', ['credit_note_id'], unique=False)
    op.create_index(op.f('ix_refunds_id'), 'refunds', ['id'], unique=False)
    op.create_index(op.f('ix_refunds_partner_id'), 'refunds', ['partner_id'], unique=False)
    op.create_index(op.f('ix_refunds_receivable_or_payable_account_id'), 'refunds', ['receivable_or_payable_account_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_refunds_receivable_or_payable_account_id'), table_name='refunds')
    op.drop_index(op.f('ix_refunds_partner_id'), table_name='refunds')
    op.drop_index(op.f('ix_refunds_id'), table_name='refunds')
    op.drop_index(op.f('ix_refunds_credit_note_id'), table_name='refunds')
    op.drop_index(op.f('ix_refunds_created_by_user_id'), table_name='refunds')
    op.drop_index(op.f('ix_refunds_bank_or_cash_account_id'), table_name='refunds')
    op.drop_index(op.f('ix_payments_receivable_or_payable_account_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_partner_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_created_by_user_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_bank_or_cash_account_id'), table_name='payments')
    op.drop_index(op.f('ix_payment_allocations_invoice'), table_name='payment_allocations')
    op.drop_index(op.f('ix_payment_allocations_id'), table_name='payment_allocations')
    op.drop_index(op.f('ix_payment_allocations_company'), table_name='payment_allocations')
    op.drop_index(op.f('ix_partners_receivable_account_id'), table_name='partners')
    op.drop_index(op.f('ix_partners_payable_account_id'), table_name='partners')
    op.drop_index(op.f('ix_partners_id'), table_name='partners')
    op.drop_index(op.f('ix_invoices_partner_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_journal_entry_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_created_by_user_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_company_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoice_lines_invoice_id'), table_name='invoice_lines')
    op.drop_index(op.f('ix_invoice_lines_id'), table_name='invoice_lines')
    op.drop_index(op.f('ix_invoice_lines_account_id'), table_name='invoice_lines')
    op.drop_index(op.f('ix_credit_notes_partner_id'), table_name='credit_notes')
    op.drop_index(op.f('ix_credit_notes_id'), table_name='credit_notes')
    op.drop_index(op.f('ix_credit_notes_created_by_user_id'), table_name='credit_notes')
    op.drop_index(op.f('ix_credit_note_lines_id'), table_name='credit_note_lines')
    op.drop_index(op.f('ix_credit_note_allocations_invoice'), table_name='credit_note_allocations')
    op.drop_index(op.f('ix_credit_note_allocations_id'), table_name='credit_note_allocations')
    op.drop_index(op.f('ix_credit_note_allocations_company'), table_name='credit_note_allocations')
