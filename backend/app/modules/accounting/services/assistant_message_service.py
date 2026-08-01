"""Assistant message dispatch service.

Contains functions that require two-phase commit semantics for idempotency:
  - ``send_conversation_message`` — commits user message before AI call, then
    commits assistant message after.  These two separate commits are intentional
    and must not be collapsed into a single unit of work.
  - ``record_confirmation_event`` — persists a system-event message; supports
    both flush-only (``commit=False``) and commit (``commit=True``) modes.

.. note::
    This file is in ``_SERVICES_COMMIT_ALLOWLIST`` because its commit calls are
    load-bearing for idempotency and crash recovery, not accidental service-layer
    commits.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.accounting.models.assistant_conversation import (
    AssistantConversation,
    AssistantMessage,
)
from app.modules.accounting.schemas.gemini_assistant_schemas import (
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
    make_pending_context_token,
)
# Import the module so that monkeypatches on
# assistant_conversation_service.dispatch_gemini_assistant are respected at
# call time (the test seam depends on attribute lookup, not a local binding).
from app.modules.accounting.services import assistant_conversation_service as _acs_module

logger = logging.getLogger(__name__)

MAX_CONTEXT_MESSAGES = 20
MAX_CONTEXT_CONTENT = 500


# ── Private helpers (duplicated from assistant_conversation_service to keep this
#    module self-contained and avoid circular imports) ─────────────────────────


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
    from app.modules.accounting.services.assistant_conversation_service import (
        _reply_from_message as _base_reply_from_message,
    )
    return _base_reply_from_message(message)


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


def _recent_history(db, *, conversation_id, before_message_id):
    from app.modules.accounting.services.assistant_conversation_service import (
        _recent_history as _base_recent_history,
    )
    return _base_recent_history(db, conversation_id=conversation_id, before_message_id=before_message_id)


def _latest_pending_transaction(db, *, conversation_id, before_message_id):
    from app.modules.accounting.services.assistant_conversation_service import (
        _latest_pending_transaction as _base,
    )
    return _base(db, conversation_id=conversation_id, before_message_id=before_message_id)


def _latest_profit_loss_grounding(db, *, conversation_id, before_message_id):
    from app.modules.accounting.services.assistant_conversation_service import (
        _latest_profit_loss_grounding as _base,
    )
    return _base(db, conversation_id=conversation_id, before_message_id=before_message_id)


def _update_automatic_title(conversation, *, message, language, reply):
    from app.modules.accounting.services.assistant_conversation_service import (
        _update_automatic_title as _base,
    )
    return _base(conversation, message=message, language=language, reply=reply)


def _get_owned_conversation(db, *, conversation_id, company_id, user_id):
    from app.modules.accounting.services.assistant_conversation_service import (
        get_owned_conversation,
    )
    return get_owned_conversation(db, conversation_id=conversation_id, company_id=company_id, user_id=user_id)


# ── Public API ────────────────────────────────────────────────────────────────


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
    """Send a user message and receive an assistant reply.

    Uses two separate commits deliberately:
    1. User message commit — ensures the user message is persisted before calling
       the AI, so it survives AI timeouts.
    2. Assistant message commit — persists the AI reply after successful generation.

    Both commits are required for idempotency guarantees.
    """
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

        conversation.last_message_at = now
        conversation.updated_at = now
        db.add_all([conversation, user_message])
        try:
            db.commit()  # Intentional: persist user message before AI call
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
    prior_grounding = _latest_profit_loss_grounding(
        db,
        conversation_id=conversation.id,
        before_message_id=user_message.id,
    )

    try:
        # Call via module attribute so tests can monkeypatch
        # assistant_conversation_service.dispatch_gemini_assistant.
        reply = _acs_module.dispatch_gemini_assistant(
            db=db,
            company_id=conversation.company_id,
            user_role=user_role,
            message=user_message.content,
            page_context=page_context,
            language=message_language,
            history=history,
            pending_transaction=pending,
            pending_context_token=pending_token,
            prior_grounding=prior_grounding,
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

    _update_automatic_title(
        conversation,
        message=user_message.content,
        language=message_language,
        reply=reply,
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
    conversation = _get_owned_conversation(
        db,
        conversation_id=conversation.id,
        company_id=conversation.company_id,
        user_id=conversation.user_id,
    )
    conversation.last_message_at = now
    conversation.updated_at = now
    db.add_all([conversation, assistant_message])
    try:
        db.commit()  # Intentional: persist assistant message after AI response
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
    commit: bool = True,
) -> AssistantMessage:
    """Persist a system-event message after a Gemini-confirmed journal entry.

    The ``commit`` parameter is False when called from ``ai_routes`` where the
    route itself commits; True when called standalone.
    """
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
    if commit:
        db.commit()  # Intentional: caller has explicitly opted in
        db.refresh(event)
    else:
        try:
            db.flush()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            raise
    return event
