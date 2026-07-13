from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.accounting.models.company import Company
    from app.modules.accounting.models.user import User


class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_assistant_conversations_status",
        ),
        Index("ix_assistant_conversations_company_id", "company_id"),
        Index("ix_assistant_conversations_user_id", "user_id"),
        Index("ix_assistant_conversations_last_message_at", "last_message_at"),
        Index(
            "ix_assistant_conversations_owner_company_activity",
            "user_id",
            "company_id",
            "last_message_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    company: Mapped[Company] = relationship()
    user: Mapped[User] = relationship()
    messages: Mapped[list[AssistantMessage]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AssistantMessage.created_at, AssistantMessage.id",
    )


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system_event')",
            name="ck_assistant_messages_role",
        ),
        CheckConstraint(
            "language IN ('en', 'ar')",
            name="ck_assistant_messages_language",
        ),
        CheckConstraint(
            "message_type IN ('text', 'journal_preview', 'report_result', "
            "'clarification', 'error', 'system_notice')",
            name="ck_assistant_messages_type",
        ),
        UniqueConstraint(
            "conversation_id",
            "client_message_id",
            name="uq_assistant_messages_client_message",
        ),
        UniqueConstraint(
            "in_reply_to_id",
            name="uq_assistant_messages_in_reply_to_id",
        ),
        Index(
            "ix_assistant_messages_conversation_created",
            "conversation_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(2), nullable=False, default="en")
    message_type: Mapped[str] = mapped_column(String(30), nullable=False, default="text")
    message_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    client_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    in_reply_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("assistant_messages.id", ondelete="CASCADE"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped[AssistantConversation] = relationship(
        back_populates="messages"
    )