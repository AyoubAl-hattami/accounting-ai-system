"""create_partners_and_invoices_tables

Revision ID: a5ac1358f2c4
Revises: b4d8c2f7a916
Create Date: 2026-09-19 11:56:03.483464
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a5ac1358f2c4"
down_revision: Union[str, Sequence[str], None] = "b4d8c2f7a916"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "partners",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("is_customer", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_vendor", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("tax_id", sa.String(length=50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("receivable_account_id", sa.Integer(), nullable=True),
        sa.Column("payable_account_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(["receivable_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payable_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_partners_company_code"),
        sa.CheckConstraint(
            "is_customer = TRUE OR is_vendor = TRUE",
            name="ck_partners_customer_or_vendor",
        ),
        sa.CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name="ck_partners_currency_iso",
        ),
    )
    op.create_index("ix_partners_company_id", "partners", ["company_id"])
    op.create_index(
        "ix_partners_company_type",
        "partners",
        ["company_id", "is_customer", "is_vendor"],
    )

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.Integer(), nullable=False),
        sa.Column("invoice_type", sa.String(length=20), nullable=False),
        sa.Column("invoice_no", sa.String(length=50), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("journal_entry_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("company_id", "invoice_type", "invoice_no", name="uq_invoices_company_type_no"),
        sa.CheckConstraint("invoice_type IN ('out_invoice', 'in_invoice')", name="ck_invoices_type"),
        sa.CheckConstraint(
            "status IN ('draft', 'posted', 'paid', 'void', 'cancelled')",
            name="ck_invoices_status",
        ),
        sa.CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name="ck_invoices_currency_iso",
        ),
        sa.CheckConstraint("total_amount >= 0", name="ck_invoices_total_positive"),
    )
    op.create_index(
        "ix_invoices_company_type_status",
        "invoices",
        ["company_id", "invoice_type", "status"],
    )
    op.create_index("ix_invoices_partner", "invoices", ["company_id", "partner_id"])

    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=4), server_default="1.0000", nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id", "line_no", name="uq_invoice_lines_invoice_line_no"),
        sa.CheckConstraint("quantity > 0", name="ck_invoice_lines_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_invoice_lines_unit_price_positive"),
    )


def downgrade() -> None:
    op.drop_table("invoice_lines")
    op.drop_table("invoices")
    op.drop_table("partners")
