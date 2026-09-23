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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.accounting.models.account import Account
    from app.modules.accounting.models.company import Company
    from app.modules.accounting.models.invoice import Invoice
    from app.modules.accounting.models.journal_entry import JournalEntry
    from app.modules.accounting.models.partner import Partner
    from app.modules.accounting.models.user import User


class CreditNote(Base):
    __tablename__ = "credit_notes"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "note_type",
            "credit_note_no",
            name="uq_credit_notes_company_type_no",
        ),
        CheckConstraint(
            "note_type IN ('customer_credit_note', 'vendor_debit_note')",
            name="ck_credit_notes_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'posted', 'void')",
            name="ck_credit_notes_status",
        ),
        CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name="ck_credit_notes_currency_iso",
        ),
        CheckConstraint("total_amount >= 0", name="ck_credit_notes_total_positive"),
        Index("ix_credit_notes_company_type_status", "company_id", "note_type", "status"),
        Index("ix_credit_notes_partner", "company_id", "partner_id"),
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

    # customer_credit_note = Customer/Sales Credit Note, vendor_debit_note = Vendor/Purchase Debit Note
    note_type: Mapped[str] = mapped_column(String(30), nullable=False)

    credit_note_no: Mapped[str] = mapped_column(String(50), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    issue_date: Mapped[date] = mapped_column(Date, nullable=False)

    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    journal_entry: Mapped[JournalEntry | None] = relationship("JournalEntry")
    created_by: Mapped[User | None] = relationship("User")

    lines: Mapped[list[CreditNoteLine]] = relationship(
        "CreditNoteLine",
        back_populates="credit_note",
        cascade="all, delete-orphan",
        order_by="CreditNoteLine.line_no",
    )

    allocations: Mapped[list[CreditNoteAllocation]] = relationship(
        "CreditNoteAllocation",
        back_populates="credit_note",
        cascade="all, delete-orphan",
        order_by="CreditNoteAllocation.id",
    )

    @property
    def allocated_amount(self) -> Decimal:
        if not self.allocations:
            return Decimal("0.00")
        return sum(
            (alloc.amount for alloc in self.allocations),
            Decimal("0.00"),
        )

    @property
    def unallocated_amount(self) -> Decimal:
        return max(Decimal("0.00"), self.total_amount - self.allocated_amount)


class CreditNoteLine(Base):
    __tablename__ = "credit_note_lines"

    __table_args__ = (
        UniqueConstraint(
            "credit_note_id",
            "line_no",
            name="uq_credit_note_lines_line_no",
        ),
        CheckConstraint("quantity > 0", name="ck_credit_note_lines_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_credit_note_lines_unit_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    credit_note_id: Mapped[int] = mapped_column(
        ForeignKey("credit_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    line_no: Mapped[int] = mapped_column(nullable=False)

    description: Mapped[str] = mapped_column(String(255), nullable=False)

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("1.0000"),
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # GL account: Sales Returns / Revenue for customer_credit_note, Purchase Returns / Expense for vendor_debit_note
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    credit_note: Mapped[CreditNote] = relationship("CreditNote", back_populates="lines")
    account: Mapped[Account] = relationship("Account")


class CreditNoteAllocation(Base):
    __tablename__ = "credit_note_allocations"

    __table_args__ = (
        UniqueConstraint(
            "credit_note_id",
            "invoice_id",
            name="uq_credit_note_allocations_note_invoice",
        ),
        CheckConstraint("amount > 0", name="ck_credit_note_allocations_amount_positive"),
        Index("ix_credit_note_allocations_company", "company_id"),
        Index("ix_credit_note_allocations_invoice", "invoice_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    credit_note_id: Mapped[int] = mapped_column(
        ForeignKey("credit_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    credit_note: Mapped[CreditNote] = relationship("CreditNote", back_populates="allocations")
    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="credit_allocations")
