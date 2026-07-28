from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CompanyUserInvitation(Base):
    __tablename__ = "company_user_invitations"
    __table_args__ = (
        CheckConstraint(
            "NOT (accepted_at IS NOT NULL AND cancelled_at IS NOT NULL)",
            name="ck_company_user_invitation_single_terminal_state",
        ),
        Index(
            "uq_company_user_invitations_live",
            "company_id",
            "normalized_email",
            unique=True,
            postgresql_where=text("accepted_at IS NULL AND cancelled_at IS NULL"),
            sqlite_where=text("accepted_at IS NULL AND cancelled_at IS NULL"),
        ),
        Index(
            "ix_company_user_invitations_company_normalized_email",
            "company_id",
            "normalized_email",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    invited_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
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

    @property
    def status(self) -> str:
        if self.accepted_at is not None:
            return "accepted"
        if self.cancelled_at is not None:
            return "cancelled"
        expires_at = self.expires_at
        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            now = now.replace(tzinfo=None)
        if expires_at < now:
            return "expired"
        return "pending"
