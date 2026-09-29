"""create_credit_notes_and_refunds_tables

Revision ID: d9e2f1a8b7c6
Revises: c8f1e2a3b4c5
Create Date: 2026-09-20 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9e2f1a8b7c6"
down_revision: Union[str, Sequence[str], None] = "c8f1e2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. credit_notes table
    op.create_table(
        "credit_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.Integer(), nullable=False),
        sa.Column("note_type", sa.String(length=30), nullable=False),
        sa.Column("credit_note_no", sa.String(length=50), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("journal_entry_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "note_type", "credit_note_no", name="uq_credit_notes_company_type_no"),
        sa.CheckConstraint("note_type IN ('customer_credit_note', 'vendor_debit_note')", name="ck_credit_notes_type"),
        sa.CheckConstraint("status IN ('draft', 'posted', 'void')", name="ck_credit_notes_status"),
        sa.CheckConstraint("currency = upper(currency) AND length(currency) = 3", name="ck_credit_notes_currency_iso"),
        sa.CheckConstraint("total_amount >= 0", name="ck_credit_notes_total_positive"),
    )
    op.create_index("ix_credit_notes_company_id", "credit_notes", ["company_id"])
    op.create_index("ix_credit_notes_company_type_status", "credit_notes", ["company_id", "note_type", "status"])
    op.create_index("ix_credit_notes_partner", "credit_notes", ["company_id", "partner_id"])
    op.create_index("ix_credit_notes_journal_entry_id", "credit_notes", ["journal_entry_id"])

    # 2. credit_note_lines table
    op.create_table(
        "credit_note_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("credit_note_id", sa.Integer(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=4), server_default="1.0000", nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["credit_note_id"], ["credit_notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credit_note_id", "line_no", name="uq_credit_note_lines_line_no"),
        sa.CheckConstraint("quantity > 0", name="ck_credit_note_lines_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_credit_note_lines_unit_price_positive"),
    )
    op.create_index("ix_credit_note_lines_credit_note_id", "credit_note_lines", ["credit_note_id"])
    op.create_index("ix_credit_note_lines_account_id", "credit_note_lines", ["account_id"])

    # 3. credit_note_allocations table
    op.create_table(
        "credit_note_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("credit_note_id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["credit_note_id"], ["credit_notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credit_note_id", "invoice_id", name="uq_credit_note_allocations_note_invoice"),
        sa.CheckConstraint("amount > 0", name="ck_credit_note_allocations_amount_positive"),
    )
    op.create_index("ix_credit_note_allocations_company_id", "credit_note_allocations", ["company_id"])
    op.create_index("ix_credit_note_allocations_credit_note_id", "credit_note_allocations", ["credit_note_id"])
    op.create_index("ix_credit_note_allocations_invoice_id", "credit_note_allocations", ["invoice_id"])

    # 4. refunds table
    op.create_table(
        "refunds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.Integer(), nullable=False),
        sa.Column("refund_type", sa.String(length=30), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("refund_date", sa.Date(), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("bank_or_cash_account_id", sa.Integer(), nullable=False),
        sa.Column("receivable_or_payable_account_id", sa.Integer(), nullable=False),
        sa.Column("credit_note_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("journal_entry_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["bank_or_cash_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["receivable_or_payable_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["credit_note_id"], ["credit_notes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("refund_type IN ('customer_refund', 'vendor_refund')", name="ck_refunds_type"),
        sa.CheckConstraint("status IN ('draft', 'posted', 'void')", name="ck_refunds_status"),
        sa.CheckConstraint("currency_code = upper(currency_code) AND length(currency_code) = 3", name="ck_refunds_currency_iso"),
        sa.CheckConstraint("amount > 0", name="ck_refunds_amount_positive"),
    )
    op.create_index("ix_refunds_company_id", "refunds", ["company_id"])
    op.create_index("ix_refunds_company_type_status", "refunds", ["company_id", "refund_type", "status"])
    op.create_index("ix_refunds_partner", "refunds", ["company_id", "partner_id"])
    op.create_index("ix_refunds_journal_entry_id", "refunds", ["journal_entry_id"])


def downgrade() -> None:
    op.drop_index("ix_refunds_journal_entry_id", table_name="refunds")
    op.drop_index("ix_refunds_partner", table_name="refunds")
    op.drop_index("ix_refunds_company_type_status", table_name="refunds")
    op.drop_index("ix_refunds_company_id", table_name="refunds")
    op.drop_table("refunds")

    op.drop_index("ix_credit_note_allocations_invoice_id", table_name="credit_note_allocations")
    op.drop_index("ix_credit_note_allocations_credit_note_id", table_name="credit_note_allocations")
    op.drop_index("ix_credit_note_allocations_company_id", table_name="credit_note_allocations")
    op.drop_table("credit_note_allocations")

    op.drop_index("ix_credit_note_lines_account_id", table_name="credit_note_lines")
    op.drop_index("ix_credit_note_lines_credit_note_id", table_name="credit_note_lines")
    op.drop_table("credit_note_lines")

    op.drop_index("ix_credit_notes_journal_entry_id", table_name="credit_notes")
    op.drop_index("ix_credit_notes_partner", table_name="credit_notes")
    op.drop_index("ix_credit_notes_company_type_status", table_name="credit_notes")
    op.drop_index("ix_credit_notes_company_id", table_name="credit_notes")
    op.drop_table("credit_notes")
