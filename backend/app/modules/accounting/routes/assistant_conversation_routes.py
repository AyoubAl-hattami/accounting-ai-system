from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.core.pagination import PaginatedResponse
from app.modules.accounting.models.assistant_conversation import AssistantConversation
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.assistant_conversation import (
    AssistantConversationCreate,
    AssistantConversationDetailRead,
    AssistantConversationMessageCreate,
    AssistantConversationPatch,
    AssistantConversationRead,
    AssistantMessageExchangeRead,
)
from app.modules.accounting.services.assistant_conversation_service import (
    create_conversation,
    delete_conversation,
    get_owned_conversation,
    list_conversation_messages,
    list_owned_conversations,
    message_to_read,
    send_conversation_message,
    update_conversation,
)
from app.modules.accounting.services.audit_service import create_audit_log

router = APIRouter(prefix="/ai/conversations", tags=["AI Assistant"])


def _conversation_read(
    conversation: AssistantConversation,
    preview: str | None = None,
) -> AssistantConversationRead:
    return AssistantConversationRead(
        id=conversation.id,
        company_id=conversation.company_id,
        title=conversation.title,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        last_message_at=conversation.last_message_at,
        last_message_preview=preview[:160] if preview else None,
    )


def _owned_or_404(
    db: Session,
    *,
    conversation_id: int,
    company_id: int,
    current_user: User,
) -> AssistantConversation:
    conversation = get_owned_conversation(
        db,
        conversation_id=conversation_id,
        company_id=company_id,
        user_id=current_user.id,
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conversation


@router.get("", response_model=PaginatedResponse[AssistantConversationRead])
def list_assistant_conversations(
    company_id: int = Query(..., ge=1),
    conversation_status: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(db=db, current_user=current_user, company_id=company_id)
    if conversation_status not in {None, "active", "archived"}:
        raise HTTPException(status_code=400, detail="Invalid conversation status")
    rows, total = list_owned_conversations(
        db,
        company_id=company_id,
        user_id=current_user.id,
        status=conversation_status,
        skip=skip,
        limit=limit,
    )
    return PaginatedResponse[AssistantConversationRead](
        items=[_conversation_read(conversation, preview) for conversation, preview in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=AssistantConversationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_assistant_conversation(
    payload: AssistantConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db, current_user=current_user, company_id=payload.company_id
    )
    conversation = create_conversation(
        db,
        company_id=payload.company_id,
        user_id=current_user.id,
        title=payload.title,
        language=payload.language,
    )
    return _conversation_read(conversation)


@router.get(
    "/{conversation_id}",
    response_model=AssistantConversationDetailRead,
)
def get_assistant_conversation(
    conversation_id: int,
    company_id: int = Query(..., ge=1),
    messages_skip: int = Query(default=0, ge=0),
    messages_limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(db=db, current_user=current_user, company_id=company_id)
    conversation = _owned_or_404(
        db,
        conversation_id=conversation_id,
        company_id=company_id,
        current_user=current_user,
    )
    messages, total = list_conversation_messages(
        db,
        conversation_id=conversation.id,
        skip=messages_skip,
        limit=messages_limit,
    )
    base = _conversation_read(conversation)
    return AssistantConversationDetailRead(
        **base.model_dump(),
        messages=[message_to_read(message) for message in messages],
        messages_total=total,
        messages_skip=messages_skip,
        messages_limit=messages_limit,
    )


@router.patch(
    "/{conversation_id}",
    response_model=AssistantConversationRead,
)
def patch_assistant_conversation(
    conversation_id: int,
    payload: AssistantConversationPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db, current_user=current_user, company_id=payload.company_id
    )
    conversation = _owned_or_404(
        db,
        conversation_id=conversation_id,
        company_id=payload.company_id,
        current_user=current_user,
    )
    updated = update_conversation(
        db,
        conversation,
        title=payload.title,
        status=payload.status,
    )
    return _conversation_read(updated)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assistant_conversation(
    conversation_id: int,
    company_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(db=db, current_user=current_user, company_id=company_id)
    conversation = _owned_or_404(
        db,
        conversation_id=conversation_id,
        company_id=company_id,
        current_user=current_user,
    )
    create_audit_log(
        db=db,
        company_id=company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="delete_assistant_conversation",
        entity_type="assistant_conversation",
        entity_id=conversation.id,
        description="Deleted an assistant conversation",
    )
    conversation = _owned_or_404(
        db,
        conversation_id=conversation_id,
        company_id=company_id,
        current_user=current_user,
    )
    delete_conversation(db, conversation)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{conversation_id}/messages",
    response_model=AssistantMessageExchangeRead,
    status_code=status.HTTP_201_CREATED,
)
def send_assistant_conversation_message(
    conversation_id: int,
    payload: AssistantConversationMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_access = ensure_company_access(
        db=db, current_user=current_user, company_id=payload.company_id
    )
    conversation = _owned_or_404(
        db,
        conversation_id=conversation_id,
        company_id=payload.company_id,
        current_user=current_user,
    )
    if conversation.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived conversations cannot receive messages",
        )
    user_message, assistant_message, reply, replay = send_conversation_message(
        db,
        conversation=conversation,
        user_role=company_access.role,
        message=payload.message,
        language=payload.language,
        page_context=payload.page_context,
        client_message_id=payload.client_message_id,
    )
    return AssistantMessageExchangeRead(
        user_message=message_to_read(user_message),
        assistant_message=message_to_read(assistant_message),
        assistant_reply=reply,
        idempotent_replay=replay,
    )