from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.ai_suggestion_schemas import (
    AiStatusResponse,
    JournalSuggestionRequest,
    JournalSuggestionResponse,
)
from app.modules.accounting.services.ai_provider_factory import (
    get_journal_suggestion_provider,
    get_provider_status,
)


router = APIRouter(
    prefix="/ai",
    tags=["AI Assistant"],
)


@router.post(
    "/journal-suggestions",
    response_model=JournalSuggestionResponse,
    status_code=status.HTTP_200_OK,
)
def suggest_journal_entry_endpoint(
    payload: JournalSuggestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
    )

    provider = get_journal_suggestion_provider()

    result = provider.suggest_journal_entry(
        description=payload.description,
        accounts=payload.accounts,
        language=payload.language,
    )

    return JournalSuggestionResponse(**result)


@router.get(
    "/status",
    response_model=AiStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_ai_status_endpoint(
    current_user: User = Depends(get_current_user),
):
    status_data = get_provider_status()
    return AiStatusResponse(**status_data)
