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
    from app.modules.accounting.models.credit_note import CreditNoteAllocation
    from app.modules.accounting.models.journal_entry import JournalEntry
    from app.modules.accounting.models.partner import Partner
    from app.modules.accounting.models.payment import PaymentAllocation
    from app.modules.accounting.models.user import User


class Invoice(Base):
    __tablename__ = "invoices"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "invoice_type",
            "invoice_no",
            name="uq_invoices_company_type_no",
        ),
        CheckConstraint(
            "invoice_type IN ('out_invoice', 'in_invoice')",
            name="ck_invoices_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'posted', 'paid', 'void', 'cancelled')",
            name="ck_invoices_status",
        ),
        CheckConstraint(
            "currency = upper(currency) AND length(currency) = 3",
            name="ck_invoices_currency_iso",
        ),
        CheckConstraint("total_amount >= 0", name="ck_invoices_total_positive"),
        Index("ix_invoices_company_type_status", "company_id", "invoice_type", "status"),
        Index("ix_invoices_partner", "company_id", "partner_id"),
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

    # out_invoice = Sales Invoice, in_invoice = Purchase Bill
    invoice_type: Mapped[str] = mapped_column(String(20), nullable=False)

    invoice_no: Mapped[str] = mapped_column(String(50), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

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

    journal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    partner: Mapped[Partner] = relationship("Partner")
    journal_entry: Mapped[JournalEntry | None] = relationship("JournalEntry")
    created_by: Mapped[User | None] = relationship("User")

    lines: Mapped[list[InvoiceLine]] = relationship(
        "InvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.line_no",
    )

    allocations: Mapped[list[PaymentAllocation]] = relationship(
        "PaymentAllocation",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )

    credit_allocations: Mapped[list[CreditNoteAllocation]] = relationship(
        "CreditNoteAllocation",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )

    @property
    def paid_amount(self) -> Decimal:
        try:
            if not self.allocations:
                return Decimal("0.00")
            return sum(
                (
                    alloc.amount
                    for alloc in self.allocations
                    if alloc.payment and alloc.payment.status == "posted"
                ),
                Decimal("0.00"),
            )
        except Exception:
            return Decimal("0.00")

    @property
    def credited_amount(self) -> Decimal:
        try:
            if not self.credit_allocations:
                return Decimal("0.00")
            return sum(
                (
                    alloc.amount
                    for alloc in self.credit_allocations
                    if alloc.credit_note and alloc.credit_note.status == "posted"
                ),
                Decimal("0.00"),
            )
        except Exception:
            return Decimal("0.00")

    @property
    def residual_amount(self) -> Decimal:
        residual = self.total_amount - self.paid_amount - self.credited_amount
        return max(Decimal("0.00"), residual)

    @property
    def payment_status(self) -> str:
        if self.status in ("draft", "void", "cancelled"):
            return "unpaid"
        settled = self.paid_amount + self.credited_amount
        if settled >= self.total_amount:
            return "paid"
        if settled > Decimal("0.00"):
            return "partially_paid"
        return "unpaid"


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    __table_args__ = (
        UniqueConstraint(
            "invoice_id",
            "line_no",
            name="uq_invoice_lines_invoice_line_no",
        ),
        CheckConstraint("quantity > 0", name="ck_invoice_lines_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_invoice_lines_unit_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"),
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

    # GL account: Sales revenue for out_invoice, Expense/Asset for in_invoice
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="lines")
    account: Mapped[Account] = relationship("Account")
