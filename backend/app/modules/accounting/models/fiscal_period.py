from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FiscalPeriod(Base):
    __tablename__ = "fiscal_periods"

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year_id",
            "period_no",
            name="uq_fiscal_periods_year_period_no",
        ),
        UniqueConstraint(
            "fiscal_year_id",
            "name",
            name="uq_fiscal_periods_year_name",
        ),
        CheckConstraint(
            "period_no >= 1 AND period_no <= 12",
            name="ck_fiscal_periods_period_no",
        ),
        CheckConstraint(
            "end_date >= start_date",
            name="ck_fiscal_periods_date_range",
        ),
        CheckConstraint(
            "status IN ('open', 'closed', 'locked')",
            name="ck_fiscal_periods_status",
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

    period_no: Mapped[int] = mapped_column(Integer, nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")

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