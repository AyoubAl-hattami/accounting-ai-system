from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.application.credit_notes.dto import (
    AllocateCreditNoteCommand,
    CreateCreditNoteAllocationCommand,
    CreateCreditNoteCommand,
    CreateCreditNoteLineCommand,
    CreditNoteQuery,
    PostCreditNoteCommand,
    VoidCreditNoteCommand,
)
from app.application.credit_notes.use_cases import (
    AllocateCreditNote,
    CreateCreditNote,
    GetCreditNote,
    ListCreditNotes,
    PostCreditNote,
    VoidCreditNote,
)
from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.infrastructure.database.sqlalchemy.repositories.credit_note_repository import (
    SqlAlchemyCreditNoteRepository,
)
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.credit_note import (
    CreditNoteAllocateRequest,
    CreditNoteCreate,
    CreditNoteListRead,
    CreditNotePostRequest,
    CreditNoteRead,
)
from app.modules.accounting.services.accounting_lookup_facade import (
    find_fiscal_period_for_date,
    find_fiscal_year_for_date,
    get_company_or_none,
)
from app.modules.accounting.services.audit_service import prepare_audit_log

router = APIRouter(
    prefix="/credit-notes",
    tags=["Credit & Debit Notes"],
)


@router.post(
    "",
    response_model=CreditNoteRead,
    status_code=status.HTTP_201_CREATED,
)
def create_credit_note_endpoint(
    payload: CreditNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
        allowed_roles={"admin", "accountant"},
    )

    company = get_company_or_none(db=db, company_id=payload.company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    lines = [
        CreateCreditNoteLineCommand(
            description=l.description,
            quantity=l.quantity,
            unit_price=l.unit_price,
            account_id=l.account_id,
        )
        for l in payload.lines
    ]

    allocations = [
        CreateCreditNoteAllocationCommand(
            invoice_id=a.invoice_id,
            amount=a.amount,
        )
        for a in payload.allocations
    ]

    command = CreateCreditNoteCommand(
        company_id=payload.company_id,
        partner_id=payload.partner_id,
        note_type=payload.note_type,
        credit_note_no=payload.credit_note_no.strip(),
        issue_date=payload.issue_date,
        currency=payload.currency.upper(),
        lines=lines,
        reference=payload.reference,
        tax_amount=payload.tax_amount,
        reason=payload.reason,
        created_by_user_id=current_user.id,
        allocations=allocations,
    )

    repository = SqlAlchemyCreditNoteRepository(db)
    try:
        credit_note = CreateCreditNote(repository).execute(command)
        prepare_audit_log(
            db=db,
            actor=current_user,
            action="create_credit_note",
            entity="credit_notes",
            entity_id=credit_note.id,
            details=f"Created {credit_note.note_type} #{credit_note.credit_note_no} for {credit_note.total_amount} {credit_note.currency}",
        )
        return credit_note
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=CreditNoteListRead,
)
def list_credit_notes_endpoint(
    company_id: int = Query(...),
    note_type: str | None = Query(None),
    partner_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    currency: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
        allowed_roles={"admin", "accountant", "viewer", "auditor"},
    )

    repository = SqlAlchemyCreditNoteRepository(db)
    query = CreditNoteQuery(
        company_id=company_id,
        note_type=note_type,
        partner_id=partner_id,
        status=status_filter,
        currency=currency.upper() if currency else None,
        start_date=start_date,
        end_date=end_date,
        search=search,
        skip=skip,
        limit=limit,
    )
    return ListCreditNotes(repository).execute(query)


@router.get(
    "/{credit_note_id}",
    response_model=CreditNoteRead,
)
def get_credit_note_endpoint(
    credit_note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyCreditNoteRepository(db)
    credit_note = GetCreditNote(repository).execute(credit_note_id)
    if credit_note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {credit_note_id} not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=credit_note.company_id,
        allowed_roles={"admin", "accountant", "viewer", "auditor"},
    )
    return credit_note


@router.post(
    "/{credit_note_id}/post",
    response_model=CreditNoteRead,
)
def post_credit_note_endpoint(
    credit_note_id: int,
    payload: CreditNotePostRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyCreditNoteRepository(db)
    credit_note = GetCreditNote(repository).execute(credit_note_id)
    if credit_note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {credit_note_id} not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=credit_note.company_id,
        allowed_roles={"admin", "accountant"},
    )

    fiscal_year_id = payload.fiscal_year_id if payload else None
    fiscal_period_id = payload.fiscal_period_id if payload else None
    receivable_or_payable_account_id = payload.receivable_or_payable_account_id if payload else None

    if not fiscal_year_id:
        fy = find_fiscal_year_for_date(db, credit_note.company_id, credit_note.issue_date)
        if not fy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No open fiscal year found for document date {credit_note.issue_date}.",
            )
        fiscal_year_id = fy.id

    if not fiscal_period_id:
        fp = find_fiscal_period_for_date(db, fiscal_year_id, credit_note.issue_date)
        if not fp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No open fiscal period found for document date {credit_note.issue_date}.",
            )
        fiscal_period_id = fp.id

    if not receivable_or_payable_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receivable or payable account ID is required to post.",
        )

    command = PostCreditNoteCommand(
        credit_note_id=credit_note_id,
        receivable_or_payable_account_id=receivable_or_payable_account_id,
        fiscal_year_id=fiscal_year_id,
        fiscal_period_id=fiscal_period_id,
        posted_by_user_id=current_user.id,
    )

    try:
        posted = PostCreditNote(repository).execute(command)
        prepare_audit_log(
            db=db,
            actor=current_user,
            action="post_credit_note",
            entity="credit_notes",
            entity_id=posted.id,
            details=f"Posted {posted.note_type} #{posted.credit_note_no} to ledger",
        )
        return posted
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/{credit_note_id}/void",
    response_model=CreditNoteRead,
)
def void_credit_note_endpoint(
    credit_note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyCreditNoteRepository(db)
    credit_note = GetCreditNote(repository).execute(credit_note_id)
    if credit_note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {credit_note_id} not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=credit_note.company_id,
        allowed_roles={"admin", "accountant"},
    )

    command = VoidCreditNoteCommand(
        credit_note_id=credit_note_id,
        voided_by_user_id=current_user.id,
    )

    try:
        voided = VoidCreditNote(repository).execute(command)
        prepare_audit_log(
            db=db,
            actor=current_user,
            action="void_credit_note",
            entity="credit_notes",
            entity_id=voided.id,
            details=f"Voided {voided.note_type} #{voided.credit_note_no}",
        )
        return voided
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/{credit_note_id}/allocate",
    response_model=CreditNoteRead,
)
def allocate_credit_note_endpoint(
    credit_note_id: int,
    payload: CreditNoteAllocateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyCreditNoteRepository(db)
    credit_note = GetCreditNote(repository).execute(credit_note_id)
    if credit_note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {credit_note_id} not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=credit_note.company_id,
        allowed_roles={"admin", "accountant"},
    )

    allocations = [
        CreateCreditNoteAllocationCommand(
            invoice_id=a.invoice_id,
            amount=a.amount,
        )
        for a in payload.allocations
    ]

    command = AllocateCreditNoteCommand(
        credit_note_id=credit_note_id,
        allocations=allocations,
    )

    try:
        allocated = AllocateCreditNote(repository).execute(command)
        prepare_audit_log(
            db=db,
            actor=current_user,
            action="allocate_credit_note",
            entity="credit_notes",
            entity_id=allocated.id,
            details=f"Allocated {allocated.note_type} #{allocated.credit_note_no} to {len(allocations)} invoices",
        )
        return allocated
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
