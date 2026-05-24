from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.accounting.models.journal_entry import JournalEntry


class JournalLine(Base):
    __tablename__ = "journal_lines"

    __table_args__ = (
        UniqueConstraint(
            "journal_entry_id",
            "line_no",
            name="uq_journal_lines_entry_line_no",
        ),
        CheckConstraint(
            "debit >= 0",
            name="ck_journal_lines_debit_non_negative",
        ),
        CheckConstraint(
            "credit >= 0",
            name="ck_journal_lines_credit_non_negative",
        ),
        CheckConstraint(
            "((debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0))",
            name="ck_journal_lines_debit_or_credit_only",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    journal_entry_id: Mapped[int] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    line_no: Mapped[int] = mapped_column(Integer, nullable=False)

    debit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    journal_entry: Mapped["JournalEntry"] = relationship(
        "JournalEntry",
        back_populates="lines",
    )