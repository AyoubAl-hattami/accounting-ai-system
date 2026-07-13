import logging
import re
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.accounting.models.assistant_conversation import (
    AssistantConversation,
    AssistantMessage,
)
from app.modules.accounting.schemas.assistant_conversation import AssistantMessageRead
from app.modules.accounting.schemas.gemini_assistant_schemas import (
    ConversationTurn,
    GeminiAssistantReply,
    PendingTransaction,
)
from app.modules.accounting.services.gemini_assistant_service import (
    detect_message_language,
    dispatch_gemini_assistant,
    make_pending_context_token,
)

logger = logging.getLogger(__name__)
MAX_CONTEXT_MESSAGES = 20
MAX_CONTEXT_CONTENT = 500


def default_conversation_title(language: str) -> str:
    return "محادثة جديدة" if language == "ar" else "New conversation"


def generate_conversation_title(message: str, language: str) -> str:
    clean = re.sub(r"\s+", " ", message).strip()
    if not clean:
        return default_conversation_title(language)
    words = clean.split(" ")[:8]
    title = " ".join(words).strip(" .,:;!?؟")
    if len(title) > 60:
        title = title[:57].rstrip() + "..."
    return title or default_conversation_title(language)


def get_owned_conversation(
    db: Session,
    *,
    conversation_id: int,
    company_id: int,
    user_id: int,
) -> AssistantConversation | None:
    return db.scalar(
        select(AssistantConversation).where(
            AssistantConversation.id == conversation_id,
            AssistantConversation.company_id == company_id,
            AssistantConversation.user_id == user_id,
        )
    )


def list_owned_conversations(
    db: Session,
    *,
    company_id: int,
    user_id: int,
    status: str | None,
    skip: int,
    limit: int,
) -> tuple[list[tuple[AssistantConversation, str | None]], int]:
    filters = [
        AssistantConversation.company_id == company_id,
        AssistantConversation.user_id == user_id,
    ]
    if status:
        filters.append(AssistantConversation.status == status)

    total = db.scalar(
        select(func.count(AssistantConversation.id)).where(*filters)
    ) or 0
    last_preview = (
        select(AssistantMessage.content)
        .where(AssistantMessage.conversation_id == AssistantConversation.id)
        .order_by(AssistantMessage.created_at.desc(), AssistantMessage.id.desc())
        .limit(1)
        .correlate(AssistantConversation)
        .scalar_subquery()
    )
    rows = db.execute(
        select(AssistantConversation, last_preview.label("last_message_preview"))
        .where(*filters)
        .order_by(
            AssistantConversation.last_message_at.desc(),
            AssistantConversation.id.desc(),
        )
        .offset(skip)
        .limit(limit)
    ).all()
    return [(row[0], row[1]) for row in rows], total


def create_conversation(
    db: Session,
    *,
    company_id: int,
    user_id: int,
    title: str | None,
    language: str,
) -> AssistantConversation:
    normalized_title = re.sub(r"\s+", " ", title or "").strip()
    conversation = AssistantConversation(
        company_id=company_id,
        user_id=user_id,
        title=(normalized_title[:120] or default_conversation_title(language)),
        status="active",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def update_conversation(
    db: Session,
    conversation: AssistantConversation,
    *,
    title: str | None,
    status: str | None,
) -> AssistantConversation:
    if title is not None:
        conversation.title = re.sub(r"\s+", " ", title).strip()[:120]
    if status is not None:
        conversation.status = status
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def delete_conversation(db: Session, conversation: AssistantConversation) -> None:
    db.delete(conversation)
    db.commit()


def list_conversation_messages(
    db: Session,
    *,
    conversation_id: int,
    skip: int,
    limit: int,
) -> tuple[list[AssistantMessage], int]:
    total = db.scalar(
        select(func.count(AssistantMessage.id)).where(
            AssistantMessage.conversation_id == conversation_id
        )
    ) or 0
    messages = list(
        db.scalars(
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == conversation_id)
            .order_by(AssistantMessage.created_at.desc(), AssistantMessage.id.desc())
            .offset(skip)
            .limit(limit)
        )
    )
    messages.reverse()
    return messages, total


def message_to_read(message: AssistantMessage) -> AssistantMessageRead:
    return AssistantMessageRead(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        language=message.language,
        message_type=message.message_type,
        metadata=message.message_metadata,
        client_message_id=message.client_message_id,
        in_reply_to_id=message.in_reply_to_id,
        created_at=message.created_at,
    )


def _safe_reply_metadata(reply: GeminiAssistantReply) -> dict:
    return reply.model_dump(
        mode="json",
        exclude={"reply", "pending_context_token"},
    )


def _message_type_for_reply(reply: GeminiAssistantReply) -> str:
    if reply.intent == "error":
        return "error"
    if reply.suggested_action:
        return "journal_preview"
    if reply.pending_transaction or reply.intent == "clarification":
        return "clarification"
    if "report" in reply.intent or reply.evidence:
        return "report_result"
    return "text"


def _reply_from_message(message: AssistantMessage) -> GeminiAssistantReply:
    metadata = dict(message.message_metadata or {})
    pending = metadata.get("pending_transaction")
    if pending:
        pending_transaction = PendingTransaction(**pending)
        metadata["pending_context_token"] = make_pending_context_token(
            pending_transaction
        )
    return GeminiAssistantReply(reply=message.content, **metadata)


def _find_idempotent_exchange(
    db: Session,
    *,
    conversation_id: int,
    client_message_id: str,
) -> tuple[AssistantMessage | None, AssistantMessage | None]:
    user_message = db.scalar(
        select(AssistantMessage).where(
            AssistantMessage.conversation_id == conversation_id,
            AssistantMessage.client_message_id == client_message_id,
            AssistantMessage.role == "user",
        )
    )
    if not user_message:
        return None, None
    assistant_message = db.scalar(
        select(AssistantMessage).where(
            AssistantMessage.in_reply_to_id == user_message.id
        )
    )
    return user_message, assistant_message


def _recent_history(
    db: Session,
    *,
    conversation_id: int,
    before_message_id: int,
) -> list[ConversationTurn]:
    recent = list(
        db.scalars(
            select(AssistantMessage)
            .where(
                AssistantMessage.conversation_id == conversation_id,
                AssistantMessage.id < before_message_id,
                AssistantMessage.role.in_(["user", "assistant"]),
            )
            .order_by(AssistantMessage.created_at.desc(), AssistantMessage.id.desc())
            .limit(MAX_CONTEXT_MESSAGES)
        )
    )
    recent.reverse()
    return [
        ConversationTurn(role=message.role, content=message.content[:MAX_CONTEXT_CONTENT])
        for message in recent
    ]


def _latest_pending_transaction(
    db: Session,
    *,
    conversation_id: int,
    before_message_id: int,
) -> PendingTransaction | None:
    latest_assistant = db.scalar(
        select(AssistantMessage)
        .where(
            AssistantMessage.conversation_id == conversation_id,
            AssistantMessage.id < before_message_id,
            AssistantMessage.role == "assistant",
        )
        .order_by(AssistantMessage.created_at.desc(), AssistantMessage.id.desc())
        .limit(1)
    )
    if not latest_assistant or not latest_assistant.message_metadata:
        return None
    pending = latest_assistant.message_metadata.get("pending_transaction")
    if not pending:
        return None
    try:
        return PendingTransaction(**pending)
    except Exception:
        return None


def send_conversation_message(
    db: Session,
    *,
    conversation: AssistantConversation,
    user_role: str,
    message: str,
    language: str,
    page_context,
    client_message_id: str,
) -> tuple[AssistantMessage, AssistantMessage, GeminiAssistantReply, bool]:
    message_language = detect_message_language(message, language)
    existing_user, existing_assistant = _find_idempotent_exchange(
        db,
        conversation_id=conversation.id,
        client_message_id=client_message_id,
    )
    if existing_user and existing_assistant:
        return (
            existing_user,
            existing_assistant,
            _reply_from_message(existing_assistant),
            True,
        )

    user_message = existing_user
    if user_message is None:
        now = datetime.now(timezone.utc)
        user_message = AssistantMessage(
            conversation_id=conversation.id,
            role="user",
            content=message.strip(),
            language=message_language,
            message_type="text",
            client_message_id=client_message_id,
        )
        if not db.scalar(
            select(func.count(AssistantMessage.id)).where(
                AssistantMessage.conversation_id == conversation.id,
                AssistantMessage.role == "user",
            )
        ):
            conversation.title = generate_conversation_title(message, message_language)
        conversation.last_message_at = now
        conversation.updated_at = now
        db.add_all([conversation, user_message])
        try:
            db.commit()
            db.refresh(user_message)
        except IntegrityError:
            db.rollback()
            user_message, existing_assistant = _find_idempotent_exchange(
                db,
                conversation_id=conversation.id,
                client_message_id=client_message_id,
            )
            if not user_message:
                raise
            if existing_assistant:
                return (
                    user_message,
                    existing_assistant,
                    _reply_from_message(existing_assistant),
                    True,
                )

    history = _recent_history(
        db,
        conversation_id=conversation.id,
        before_message_id=user_message.id,
    )
    pending = _latest_pending_transaction(
        db,
        conversation_id=conversation.id,
        before_message_id=user_message.id,
    )
    pending_token = make_pending_context_token(pending) if pending else None

    try:
        reply = dispatch_gemini_assistant(
            db=db,
            company_id=conversation.company_id,
            user_role=user_role,
            message=user_message.content,
            page_context=page_context,
            language=message_language,
            history=history,
            pending_transaction=pending,
            pending_context_token=pending_token,
        )
    except Exception as exc:
        logger.warning(
            "Persistent assistant response failed safely: %s", type(exc).__name__
        )
        db.rollback()
        safe_message = (
            "تعذر إكمال الرد الآن. يرجى المحاولة مرة أخرى."
            if message_language == "ar"
            else "The response could not be completed. Please try again."
        )
        reply = GeminiAssistantReply(
            reply=safe_message,
            intent="error",
            confidence="low",
            data_sources=[],
        )

    assistant_message = AssistantMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=reply.reply,
        language=message_language,
        message_type=_message_type_for_reply(reply),
        message_metadata=_safe_reply_metadata(reply),
        in_reply_to_id=user_message.id,
    )
    now = datetime.now(timezone.utc)
    conversation = get_owned_conversation(
        db,
        conversation_id=conversation.id,
        company_id=conversation.company_id,
        user_id=conversation.user_id,
    )
    conversation.last_message_at = now
    conversation.updated_at = now
    db.add_all([conversation, assistant_message])
    try:
        db.commit()
        db.refresh(assistant_message)
    except IntegrityError:
        db.rollback()
        existing_assistant = db.scalar(
            select(AssistantMessage).where(
                AssistantMessage.in_reply_to_id == user_message.id
            )
        )
        if not existing_assistant:
            raise
        return (
            user_message,
            existing_assistant,
            _reply_from_message(existing_assistant),
            True,
        )

    return user_message, assistant_message, reply, False

def record_confirmation_event(
    db: Session,
    *,
    conversation: AssistantConversation,
    entry_no: str,
    language: str,
) -> AssistantMessage:
    latest_preview = db.scalar(
        select(AssistantMessage)
        .where(
            AssistantMessage.conversation_id == conversation.id,
            AssistantMessage.role == "assistant",
            AssistantMessage.message_type == "journal_preview",
        )
        .order_by(AssistantMessage.created_at.desc(), AssistantMessage.id.desc())
        .limit(1)
    )
    if latest_preview and latest_preview.message_metadata:
        metadata = dict(latest_preview.message_metadata)
        metadata["suggested_action"] = None
        metadata["pending_transaction"] = None
        latest_preview.message_metadata = metadata
        db.add(latest_preview)

    content = (
        f"✅ تم إنشاء القيد المسودة بنجاح! رقم القيد: **{entry_no}**\n"
        "ملاحظة: القيود المسودة لا تظهر في التقارير المالية حتى يتم ترحيلها."
        if language == "ar"
        else f"✅ Draft journal entry created! Entry No: **{entry_no}**\n"
        "Note: draft entries do not affect financial reports until posted."
    )
    event = AssistantMessage(
        conversation_id=conversation.id,
        role="system_event",
        content=content,
        language=language,
        message_type="system_notice",
        message_metadata={"intent": "action_confirmed"},
    )
    now = datetime.now(timezone.utc)
    conversation.last_message_at = now
    conversation.updated_at = now
    db.add_all([conversation, event])
    db.commit()
    db.refresh(event)
    return event