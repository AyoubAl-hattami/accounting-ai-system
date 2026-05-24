from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    actor: Mapped[str] = mapped_column(String(100), nullable=False, default="system")

    action: Mapped[str] = mapped_column(String(100), nullable=False)

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )