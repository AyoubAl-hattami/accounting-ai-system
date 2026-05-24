from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.accounting.schemas.journal import (
    JournalEntryCreate,
    JournalEntryRead,
    JournalEntryUpdate,
    JournalEntryReverseCreate,
    
)
from app.modules.accounting.services.journal_service import (
    create_journal_entry,
    find_fiscal_period_for_date,
    find_fiscal_year_for_date,
    get_account,
    get_company_or_none,
    get_journal_entry,
    get_journal_entry_by_no,
    list_journal_entries,
    update_journal_entry,
    calculate_journal_totals,
    mark_journal_entry_reviewed,
    post_journal_entry,
    reverse_journal_entry,
    void_journal_entry,
)
from app.modules.accounting.services.audit_service import create_audit_log


router = APIRouter(
    prefix="/journal-entries",
    tags=["Journal Entries"],
)


def validate_journal_accounts(
    db: Session,
    company_id: int,
    payload: JournalEntryCreate,
):
    for line in payload.lines:
        account = get_account(db=db, account_id=line.account_id)

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {line.account_id}",
            )

        if account.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account {line.account_id} does not belong to this company",
            )

        if not account.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account {line.account_id} is inactive",
            )


@router.post(
    "",
    response_model=JournalEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_journal_entry_endpoint(
    payload: JournalEntryCreate,
    db: Session = Depends(get_db),
):
    company = get_company_or_none(db=db, company_id=payload.company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    existing_entry = get_journal_entry_by_no(
        db=db,
        company_id=payload.company_id,
        entry_no=payload.entry_no,
    )

    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Journal entry number already exists for this company",
        )

    fiscal_year = find_fiscal_year_for_date(
        db=db,
        company_id=payload.company_id,
        entry_date=payload.entry_date,
    )

    if not fiscal_year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fiscal year found for this entry date",
        )

    if fiscal_year.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal year is not open",
        )

    fiscal_period = find_fiscal_period_for_date(
        db=db,
        company_id=payload.company_id,
        entry_date=payload.entry_date,
    )

    if not fiscal_period:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fiscal period found for this entry date",
        )

    if fiscal_period.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal period is not open",
        )

    if fiscal_period.fiscal_year_id != fiscal_year.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal period does not belong to the fiscal year",
        )

    validate_journal_accounts(
        db=db,
        company_id=payload.company_id,
        payload=payload,
    )
    journal_entry = create_journal_entry(
        db=db,
        payload=payload,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
    )

    create_audit_log(
        db=db,
        company_id=journal_entry.company_id,
        action="create_journal_entry",
        entity_type="journal_entry",
        entity_id=journal_entry.id,
        description=f"Created journal entry {journal_entry.entry_no}",
    )

    return journal_entry

    

@router.get(
    "",
    response_model=list[JournalEntryRead],
)
def list_journal_entries_endpoint(
    company_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    allowed_statuses = {"draft", "reviewed", "posted", "void", "reversed"}

    if status_filter is not None and status_filter not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid journal entry status",
        )

    return list_journal_entries(
        db=db,
        company_id=company_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{journal_entry_id}",
    response_model=JournalEntryRead,
)
def get_journal_entry_endpoint(
    journal_entry_id: int,
    db: Session = Depends(get_db),
):
    journal_entry = get_journal_entry(
        db=db,
        journal_entry_id=journal_entry_id,
    )

    if not journal_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )

    return journal_entry


@router.patch(
    "/{journal_entry_id}",
    response_model=JournalEntryRead,
)
def update_journal_entry_endpoint(
    journal_entry_id: int,
    payload: JournalEntryUpdate,
    db: Session = Depends(get_db),
):
    journal_entry = get_journal_entry(
        db=db,
        journal_entry_id=journal_entry_id,
    )

    if not journal_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )

    if journal_entry.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft journal entries can be updated",
        )

    fiscal_year = None
    fiscal_period = None

    if payload.entry_date is not None:
        fiscal_year = find_fiscal_year_for_date(
            db=db,
            company_id=journal_entry.company_id,
            entry_date=payload.entry_date,
        )

        if not fiscal_year:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fiscal year found for this entry date",
            )

        if fiscal_year.status != "open":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fiscal year is not open",
            )

        fiscal_period = find_fiscal_period_for_date(
            db=db,
            company_id=journal_entry.company_id,
            entry_date=payload.entry_date,
        )

        if not fiscal_period:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fiscal period found for this entry date",
            )

        if fiscal_period.status != "open":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fiscal period is not open",
            )

        if fiscal_period.fiscal_year_id != fiscal_year.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fiscal period does not belong to the fiscal year",
            )

    updated_entry = update_journal_entry(
        db=db,
        journal_entry=journal_entry,
        payload=payload,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
    )

    create_audit_log(
        db=db,
        company_id=updated_entry.company_id,
        action="update_journal_entry",
        entity_type="journal_entry",
        entity_id=updated_entry.id,
        description=f"Updated draft journal entry {updated_entry.entry_no}",
    )

    return updated_entry
@router.post(
    "/{journal_entry_id}/review",
    response_model=JournalEntryRead,
)
def review_journal_entry_endpoint(
    journal_entry_id: int,
    db: Session = Depends(get_db),
):
    journal_entry = get_journal_entry(
        db=db,
        journal_entry_id=journal_entry_id,
    )

    if not journal_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )

    if journal_entry.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft journal entries can be reviewed",
        )

    total_debit, total_credit = calculate_journal_totals(journal_entry)

    if total_debit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total debit must be greater than zero",
        )

    if total_debit != total_credit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Journal entry is not balanced",
        )

    reviewed_entry = mark_journal_entry_reviewed(
        db=db,
        journal_entry=journal_entry,
    )

    create_audit_log(
        db=db,
        company_id=reviewed_entry.company_id,
        action="review_journal_entry",
        entity_type="journal_entry",
        entity_id=reviewed_entry.id,
        description=f"Reviewed journal entry {reviewed_entry.entry_no}",
    )

    return reviewed_entry

@router.post(
    "/{journal_entry_id}/post",
    response_model=JournalEntryRead,
)
def post_journal_entry_endpoint(
    journal_entry_id: int,
    db: Session = Depends(get_db),
):
    journal_entry = get_journal_entry(
        db=db,
        journal_entry_id=journal_entry_id,
    )

    if not journal_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )

    if journal_entry.status not in {"draft", "reviewed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft or reviewed journal entries can be posted",
        )

    fiscal_year = find_fiscal_year_for_date(
        db=db,
        company_id=journal_entry.company_id,
        entry_date=journal_entry.entry_date,
    )

    if not fiscal_year or fiscal_year.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal year is not open",
        )

    fiscal_period = find_fiscal_period_for_date(
        db=db,
        company_id=journal_entry.company_id,
        entry_date=journal_entry.entry_date,
    )

    if not fiscal_period or fiscal_period.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal period is not open",
        )

    total_debit, total_credit = calculate_journal_totals(journal_entry)

    if total_debit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total debit must be greater than zero",
        )

    if total_debit != total_credit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Journal entry is not balanced",
        )

    posted_entry = post_journal_entry(
        db=db,
        journal_entry=journal_entry,
    )

    create_audit_log(
        db=db,
        company_id=posted_entry.company_id,
        action="post_journal_entry",
        entity_type="journal_entry",
        entity_id=posted_entry.id,
        description=f"Posted journal entry {posted_entry.entry_no}",
    )

    return posted_entry
@router.post(
    "/{journal_entry_id}/reverse",
    response_model=JournalEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def reverse_journal_entry_endpoint(
    journal_entry_id: int,
    payload: JournalEntryReverseCreate,
    db: Session = Depends(get_db),
):
    original_entry = get_journal_entry(
        db=db,
        journal_entry_id=journal_entry_id,
    )

    if not original_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )

    if original_entry.status != "posted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only posted journal entries can be reversed",
        )

    existing_reversal_no = get_journal_entry_by_no(
        db=db,
        company_id=original_entry.company_id,
        entry_no=payload.entry_no,
    )

    if existing_reversal_no:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Journal entry number already exists for this company",
        )

    fiscal_year = find_fiscal_year_for_date(
        db=db,
        company_id=original_entry.company_id,
        entry_date=payload.entry_date,
    )

    if not fiscal_year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fiscal year found for this reversal date",
        )

    if fiscal_year.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal year is not open",
        )

    fiscal_period = find_fiscal_period_for_date(
        db=db,
        company_id=original_entry.company_id,
        entry_date=payload.entry_date,
    )

    if not fiscal_period:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fiscal period found for this reversal date",
        )

    if fiscal_period.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal period is not open",
        )

    if fiscal_period.fiscal_year_id != fiscal_year.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiscal period does not belong to the fiscal year",
        )

    reversal_entry = reverse_journal_entry(
        db=db,
        original_entry=original_entry,
        payload=payload,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,

    )

    create_audit_log(
        db=db,
        company_id=reversal_entry.company_id,
        action="reverse_journal_entry",
        entity_type="journal_entry",
        entity_id=reversal_entry.id,
        description=f"Created reversal journal entry {reversal_entry.entry_no} for {original_entry.entry_no}",
    )

    return reversal_entry
@router.post(
    "/{journal_entry_id}/void",
    response_model=JournalEntryRead,
)
def void_journal_entry_endpoint(
    journal_entry_id: int,
    db: Session = Depends(get_db),
):
    journal_entry = get_journal_entry(
        db=db,
        journal_entry_id=journal_entry_id,
    )

    if not journal_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )

    if journal_entry.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft journal entries can be voided",
        )

    voided_entry = void_journal_entry(
        db=db,
        journal_entry=journal_entry,
    )

    create_audit_log(
        db=db,
        company_id=voided_entry.company_id,
        action="void_journal_entry",
        entity_type="journal_entry",
        entity_id=voided_entry.id,
        description=f"Voided draft journal entry {voided_entry.entry_no}",
    )

    return voided_entry