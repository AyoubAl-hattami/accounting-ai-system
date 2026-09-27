"""Pieces shared by assistant_conversation_service and assistant_message_service.

Both modules handle one conversational exchange -- a user message and the reply
recorded against it -- and both needed the same three helpers and the same two
context limits.  They were byte-identical copies, carrying the comment
"duplicated from assistant_conversation_service to keep this module
self-contained and avoid circular imports".

That justification was measured and is not true.  Deleting the copies and
importing them from assistant_conversation_service at module scope imports
cleanly; the graph is acyclic because assistant_conversation_service defers its
own imports of assistant_message_service into function bodies.  A real cycle --
both modules importing each other at module scope -- does fail, with
"cannot import name ... from partially initialized module", so the hazard is
real in general; it just was not what these copies were avoiding.

They live here rather than in either module so neither has to depend on the
other for them, which is what keeps that hazard from returning through this
door.

Exported without the leading underscore the copies carried, since crossing a
module boundary is exactly what a name starting with `_` says it does not do.
Both importers alias them back on import, so no call site changes.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.accounting.models.assistant_conversation import AssistantMessage
from app.modules.accounting.schemas.gemini_assistant_schemas import (
    GeminiAssistantReply,
)


# How much prior conversation is replayed to the model, and how much of each
# message. Shared so the two entry points cannot drift into different limits.
MAX_CONTEXT_MESSAGES = 20
MAX_CONTEXT_CONTENT = 500


def safe_reply_metadata(reply: GeminiAssistantReply) -> dict:
    return reply.model_dump(
        mode="json",
        exclude={"reply", "pending_context_token"},
    )


def message_type_for_reply(reply: GeminiAssistantReply) -> str:
    if reply.intent == "error":
        return "error"
    if reply.suggested_action:
        return "journal_preview"
    if reply.pending_transaction or reply.intent == "clarification":
        return "clarification"
    if "report" in reply.intent or reply.evidence:
        return "report_result"
    return "text"


def find_idempotent_exchange(
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
