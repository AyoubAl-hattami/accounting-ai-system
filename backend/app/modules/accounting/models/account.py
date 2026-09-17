from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Account(Base):
    __tablename__ = "accounts"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "code",
            name="uq_accounts_company_code",
        ),
        CheckConstraint(
            "account_type IN ('asset', 'liability', 'equity', 'income', 'expense')",
            name="ck_accounts_account_type",
        ),
        CheckConstraint(
            "account_subtype IS NULL OR account_subtype IN ("
            "'bank', 'cash', 'e_wallet', 'receivable', 'payable', "
            "'revenue', 'expense', 'other')",
            name="ck_accounts_account_subtype",
        ),
        CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name="ck_accounts_currency_iso",
        ),
        # Reports total one currency at a time, and always within one company.
        # Declared here and not only in the migration: the CI drift check
        # compares the models against the schema and fails on either one alone.
        Index("ix_accounts_company_currency", "company_id", "currency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    account_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Optional presentation hint (bank / cash / e_wallet / …).  Reports classify
    # strictly by account_type; this only groups accounts for humans and helps
    # the assistant resolve "from the wallet" to a company-specific account.
    account_subtype: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # The currency this account is kept in.
    #
    # A company holding riyals and dollars keeps a separate account for each.
    # Every line of one journal entry must reference accounts of the SAME
    # currency, because debit == credit only means anything within one unit --
    # and the reports total one currency at a time for the same reason.
    #
    # There is no conversion here and no rate table: this records which unit a
    # balance is in, it does not translate between units.
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )