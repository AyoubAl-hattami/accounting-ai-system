from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
    text,
)
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
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    action: Mapped[str] = mapped_column(String(100), nullable=False)

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Declared here as well as in revision d4e9a1c73b62, which builds them
    # CONCURRENTLY.  The revision remains the thing that creates them; these
    # exist so Base.metadata matches the database.
    #
    # Without them `alembic revision --autogenerate` sees two indexes in the
    # database that the models do not mention and emits drop_index for both --
    # a generated migration that silently removes the indexes the audit page
    # depends on, turning its page-one query back into a 35 ms sort.
    __table_args__ = (
        Index(
            "ix_audit_logs_company_created",
            "company_id",
            text("created_at DESC"),
        ),
        Index(
            "ix_audit_logs_company_entity",
            "company_id",
            "entity_type",
            "entity_id",
            text("created_at DESC"),
        ),
    )