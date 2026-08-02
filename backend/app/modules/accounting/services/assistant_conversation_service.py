import logging
import re
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import flush_or_rollback
from app.modules.accounting.models.assistant_conversation import (
    AssistantConversation,
    AssistantMessage,
)
from app.modules.accounting.schemas.assistant_conversation import AssistantMessageRead
from app.modules.accounting.schemas.gemini_assistant_schemas import (
    ConversationTurn,
    GeminiAssistantReply,
    PendingTransaction,
    ProfitAndLossGrounding,
    BalanceSheetGrounding,
    TrialBalanceGrounding,
    AccountLedgerGrounding,
    GeneralLedgerGrounding,
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


def _safe_title_excerpt(message: str, language: str) -> str:
    clean = re.sub(r"\s+", " ", message).strip()
    clean = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "", clean)
    clean = re.sub(r"https?://\S+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(
        r"(?i)\b(password|token|api[_ -]?key|secret|jwt)\b\s*[:=]?\s*\S*",
        "",
        clean,
    )
    clean = re.sub(r"\b\d{6,}\b", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip(" .,:;!?؟،؛")
    if not clean:
        return default_conversation_title(language)
    words = clean.split(" ")[:7]
    title = " ".join(words)
    return title if len(title) <= 60 else title[:57].rstrip() + "..."


def generate_conversation_title(message: str, language: str, intent: str) -> str:
    normalized = re.sub(r"\s+", " ", message).strip().lower()
    if language == "ar":
        if "كهرب" in normalized:
            return "مصروف كهرباء"
        if "صافي الربح" in normalized or "صافي ربح" in normalized:
            return "تحليل صافي الربح"
        if "المبيعات" in normalized or "مبيعات" in normalized:
            return "تحليل المبيعات"
        if "الإيرادات" in normalized or "الايرادات" in normalized:
            return "تحليل الإيرادات"
        if "قيود" in normalized and "البنك" in normalized:
            return "قيود البنك"
        if intent == "identity":
            return "المساعد المحاسبي"
        if "report" in intent:
            return "تحليل مالي"
        if intent in {"journal_question", "trace_amount"}:
            return "القيود المحاسبية"
        if intent in {"create_journal_draft", "clarification"}:
            return "مسودة قيد محاسبي"
    else:
        if "electric" in normalized:
            return "Electricity expense"
        if "net profit" in normalized:
            return "Net profit analysis"
        if "sales" in normalized:
            return "Sales analysis"
        if "revenue" in normalized:
            return "Revenue analysis"
        if "bank" in normalized and ("journal" in normalized or "entries" in normalized):
            return "Bank journal entries"
        if intent == "identity":
            return "Accounting assistant"
        if "report" in intent:
            return "Financial analysis"
        if intent in {"journal_question", "trace_amount"}:
            return "Journal entries"
        if intent in {"create_journal_draft", "clarification"}:
            return "Draft journal entry"
    return _safe_title_excerpt(message, language)


def _reply_is_meaningful(reply: GeminiAssistantReply) -> bool:
    if reply.intent in {"greeting", "error", "access_denied", "unknown"}:
        return False
    if reply.intent == "clarification":
        return bool(reply.pending_transaction or reply.suggested_action)
    return True


def _update_automatic_title(
    conversation: AssistantConversation,
    *,
    message: str,
    language: str,
    reply: GeminiAssistantReply,
) -> None:
    if conversation.title_source in {"manual", "auto"}:
        return
    if reply.intent == "greeting":
        conversation.title = default_conversation_title(language)
        conversation.title_source = "greeting"
        return
    if not _reply_is_meaningful(reply):
        return
    conversation.title = generate_conversation_title(message, language, reply.intent)
    conversation.title_source = "auto"

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


def _escaped_search_pattern(search: str) -> str:
    escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def list_owned_conversations(
    db: Session,
    *,
    company_id: int,
    user_id: int,
    status: str | None,
    search: str | None,
    skip: int,
    limit: int,
) -> tuple[list[tuple[AssistantConversation, str | None]], int]:
    last_preview = (
        select(AssistantMessage.content)
        .where(AssistantMessage.conversation_id == AssistantConversation.id)
        .order_by(AssistantMessage.created_at.desc(), AssistantMessage.id.desc())
        .limit(1)
        .correlate(AssistantConversation)
        .scalar_subquery()
    )
    filters = [
        AssistantConversation.company_id == company_id,
        AssistantConversation.user_id == user_id,
    ]
    if status:
        filters.append(AssistantConversation.status == status)
    normalized_search = re.sub(r"\s+", " ", search or "").strip()
    if normalized_search:
        pattern = _escaped_search_pattern(normalized_search)
        filters.append(
            or_(
                AssistantConversation.title.ilike(pattern, escape="\\"),
                last_preview.ilike(pattern, escape="\\"),
            )
        )

    total = db.scalar(
        select(func.count(AssistantConversation.id)).where(*filters)
    ) or 0
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
        title=(normalized_title[:60] or default_conversation_title(language)),
        title_source="manual" if normalized_title else "fallback",
        status="active",
    )
    db.add(conversation)
    flush_or_rollback(db)
    return conversation


def update_conversation(
    db: Session,
    conversation: AssistantConversation,
    *,
    title: str | None,
    status: str | None,
) -> AssistantConversation:
    if title is not None:
        normalized_title = re.sub(r"\s+", " ", title).strip()
        if not normalized_title:
            raise ValueError("Conversation title cannot be empty")
        conversation.title = normalized_title[:60]
        conversation.title_source = "manual"
    if status is not None:
        conversation.status = status
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(conversation)
    flush_or_rollback(db)
    return conversation

def delete_conversation(db: Session, conversation: AssistantConversation) -> None:
    db.delete(conversation)
    flush_or_rollback(db)


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


def _latest_profit_loss_grounding(
    db: Session,
    *,
    conversation_id: int,
    before_message_id: int,
) -> dict | None:
    """Load only the newest valid P&L grounding from this owned conversation."""
    messages = list(db.scalars(
        select(AssistantMessage)
        .where(
            AssistantMessage.conversation_id == conversation_id,
            AssistantMessage.id < before_message_id,
            AssistantMessage.role == "assistant",
        )
        .order_by(AssistantMessage.created_at.desc(), AssistantMessage.id.desc())
        .limit(MAX_CONTEXT_MESSAGES)
    ))
    for message in messages:
        grounding_data = (message.message_metadata or {}).get("grounding")
        if not isinstance(grounding_data, dict):
            continue
        grounding = None
        for model in (ProfitAndLossGrounding, BalanceSheetGrounding, TrialBalanceGrounding, AccountLedgerGrounding, GeneralLedgerGrounding):
            try:
                candidate = model.model_validate(grounding_data)
            except Exception:
                continue
            if candidate.status == "grounded":
                grounding = candidate
                break
        if grounding is None:
            continue
        if grounding.kind == "profit_and_loss" and (grounding.period is None or grounding.metrics is None):
            continue
        return grounding.model_dump(mode="json")
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
) -> "tuple[AssistantMessage, AssistantMessage, GeminiAssistantReply, bool]":
    """Delegate to assistant_message_service (moved for Phase 42 clean boundary)."""
    from app.modules.accounting.services.assistant_message_service import (
        send_conversation_message as _send,
    )
    return _send(
        db,
        conversation=conversation,
        user_role=user_role,
        message=message,
        language=language,
        page_context=page_context,
        client_message_id=client_message_id,
    )


def record_confirmation_event(
    db: Session,
    *,
    conversation: AssistantConversation,
    entry_no: str,
    language: str,
    commit: bool = True,
) -> AssistantMessage:
    """Delegate to assistant_message_service (moved for Phase 42 clean boundary)."""
    from app.modules.accounting.services.assistant_message_service import (
        record_confirmation_event as _record,
    )
    return _record(db, conversation=conversation, entry_no=entry_no, language=language, commit=commit)

