from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.accounting.models.journal_line import JournalLine


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "entry_no",
            name="uq_journal_entries_company_entry_no",
        ),
        CheckConstraint(
            "status IN ('draft', 'reviewed', 'posted', 'void', 'reversed')",
            name="ck_journal_entries_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    fiscal_year_id: Mapped[int] = mapped_column(
        ForeignKey("fiscal_years.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    fiscal_period_id: Mapped[int] = mapped_column(
        ForeignKey("fiscal_periods.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    entry_no: Mapped[str] = mapped_column(String(50), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    reversal_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    lines: Mapped[list["JournalLine"]] = relationship(
        "JournalLine",
        back_populates="journal_entry",
        cascade="all, delete-orphan",
        lazy="selectin",
    )