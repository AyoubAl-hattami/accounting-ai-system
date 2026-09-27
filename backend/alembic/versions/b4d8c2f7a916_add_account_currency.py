"""Give every account a currency.

A company that holds riyals and dollars keeps a separate account for each. The
column records which unit a balance is in; it does not convert between units,
and no rate table is introduced here.

Backfill takes each company's base_currency rather than a global default, so an
existing book keeps meaning exactly what it meant before this ran: one currency,
the company's own.

Revision ID: b4d8c2f7a916
Revises: a7f3e6b21c48
"""

import sqlalchemy as sa
from alembic import op

revision = "b4d8c2f7a916"
down_revision = "a7f3e6b21c48"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable first so the table can be rewritten without a default that would
    # be wrong for every company whose base currency is not USD.
    op.add_column(
        "accounts",
        sa.Column("currency", sa.String(length=3), nullable=True),
    )

    op.execute(
        """
        UPDATE accounts
        SET currency = upper(companies.base_currency)
        FROM companies
        WHERE companies.id = accounts.company_id
        """
    )

    # A company row could in principle be missing for an orphaned account; those
    # would block the NOT NULL below, so they are given the documented default
    # rather than failing the migration.
    op.execute("UPDATE accounts SET currency = 'USD' WHERE currency IS NULL")

    op.alter_column("accounts", "currency", nullable=False)

    op.create_check_constraint(
        "ck_accounts_currency_iso",
        "accounts",
        "currency = upper(currency) AND length(currency) = 3",
    )

    # Reports total one currency at a time, and always within one company.
    op.create_index(
        "ix_accounts_company_currency",
        "accounts",
        ["company_id", "currency"],
    )


def downgrade() -> None:
    op.drop_index("ix_accounts_company_currency", table_name="accounts")
    op.drop_constraint("ck_accounts_currency_iso", "accounts", type_="check")
    op.drop_column("accounts", "currency")
