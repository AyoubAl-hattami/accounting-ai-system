from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.accounting.schemas.gemini_assistant_schemas import (
    GeminiAssistantReply,
    PageContext,
)


ConversationStatus = Literal["active", "archived"]
ConversationTitleSource = Literal["fallback", "greeting", "auto", "manual"]


class AssistantConversationCreate(BaseModel):
    company_id: int = Field(..., ge=1)
    title: str | None = Field(default=None, max_length=60)
    language: Literal["en", "ar"] = "en"

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Conversation title cannot be empty")
        return normalized


class AssistantConversationPatch(BaseModel):
    company_id: int = Field(..., ge=1)
    title: str | None = Field(default=None, max_length=60)
    status: ConversationStatus | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Conversation title cannot be empty")
        return normalized

    @model_validator(mode="after")
    def require_change(self):
        if self.title is None and self.status is None:
            raise ValueError("A title or status change is required")
        return self


class AssistantConversationRead(BaseModel):
    id: int
    company_id: int
    title: str
    title_source: ConversationTitleSource
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    last_message_preview: str | None = None


class AssistantMessageRead(BaseModel):
    id: int
    conversation_id: int
    role: Literal["user", "assistant", "system_event"]
    content: str
    language: Literal["en", "ar"]
    message_type: Literal[
        "text",
        "journal_preview",
        "report_result",
        "clarification",
        "error",
        "system_notice",
    ]
    metadata: dict[str, Any] | None = None
    client_message_id: str | None = None
    in_reply_to_id: int | None = None
    created_at: datetime


class AssistantConversationDetailRead(AssistantConversationRead):
    messages: list[AssistantMessageRead]
    messages_total: int
    messages_skip: int
    messages_limit: int


class AssistantConversationMessageCreate(BaseModel):
    company_id: int = Field(..., ge=1)
    message: str = Field(..., min_length=1, max_length=2000)
    language: Literal["en", "ar"] = "en"
    page_context: PageContext = Field(default_factory=PageContext)
    client_message_id: str = Field(..., min_length=8, max_length=100)


class AssistantMessageExchangeRead(BaseModel):
    conversation: AssistantConversationRead
    user_message: AssistantMessageRead
    assistant_message: AssistantMessageRead
    assistant_reply: GeminiAssistantReply
    idempotent_replay: bool = False