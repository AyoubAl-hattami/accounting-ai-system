from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.accounting.models.account import Account
    from app.modules.accounting.models.company import Company
    from app.modules.accounting.models.credit_note import CreditNote
    from app.modules.accounting.models.journal_entry import JournalEntry
    from app.modules.accounting.models.partner import Partner
    from app.modules.accounting.models.user import User


class Refund(Base):
    __tablename__ = "refunds"

    __table_args__ = (
        CheckConstraint(
            "refund_type IN ('customer_refund', 'vendor_refund')",
            name="ck_refunds_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'posted', 'void')",
            name="ck_refunds_status",
        ),
        CheckConstraint(
            "currency_code = upper(currency_code) AND length(currency_code) = 3",
            name="ck_refunds_currency_iso",
        ),
        CheckConstraint("amount > 0", name="ck_refunds_amount_positive"),
        Index("ix_refunds_company_type_status", "company_id", "refund_type", "status"),
        Index("ix_refunds_partner", "company_id", "partner_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    partner_id: Mapped[int] = mapped_column(
        ForeignKey("partners.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # customer_refund (outflow to customer) or vendor_refund (inflow from vendor)
    refund_type: Mapped[str] = mapped_column(String(30), nullable=False)

    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    refund_date: Mapped[date] = mapped_column(Date, nullable=False)

    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)

    bank_or_cash_account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    receivable_or_payable_account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    credit_note_id: Mapped[int | None] = mapped_column(
        ForeignKey("credit_notes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    journal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

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

    company: Mapped[Company] = relationship("Company")
    partner: Mapped[Partner] = relationship("Partner")
    bank_or_cash_account: Mapped[Account] = relationship(
        "Account",
        foreign_keys=[bank_or_cash_account_id],
    )
    receivable_or_payable_account: Mapped[Account] = relationship(
        "Account",
        foreign_keys=[receivable_or_payable_account_id],
    )
    credit_note: Mapped[CreditNote | None] = relationship("CreditNote")
    journal_entry: Mapped[JournalEntry | None] = relationship("JournalEntry")
    created_by: Mapped[User | None] = relationship("User")
