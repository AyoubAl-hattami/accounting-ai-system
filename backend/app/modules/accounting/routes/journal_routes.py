from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.journals.dto import (
    CreateJournalEntryCommand,
    CreateJournalLineCommand,
    CreateOpeningBalanceCommand,
    PostJournalEntryCommand,
    ReviewJournalEntryCommand,
    ReverseJournalEntryCommand,
    UpdateJournalEntryCommand,
    VoidJournalEntryCommand,
)
from app.application.journals.use_cases import (
    calculate_journal_totals,
    CreateJournalEntry,
    CreateOpeningBalance,
    GetJournalEntry,
    ListJournalEntries,
    PostJournalEntry,
    ReviewJournalEntry,
    ReverseJournalEntry,
    UpdateJournalEntry,
    VoidJournalEntry,
)
from app.infrastructure.database.sqlalchemy.repositories.journal_repository import (
    SqlAlchemyJournalRepository,
)
from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.core.pagination import PaginatedResponse
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.journal import (
    JournalEntryCreate,
    JournalEntryRead,
    JournalEntryReverseCreate,
    JournalEntryUpdate,
    OpeningBalanceCreate,
)
from app.modules.accounting.services.audit_service import (
    prepare_audit_log,
)
from app.modules.accounting.services.accounting_lookup_facade import (
    find_fiscal_period_for_date,
    find_fiscal_year_for_date,
    get_account,
    get_company_or_none,
    get_journal_entry,
    get_journal_entry_by_no,
    get_reversal_for_entry,
)


router = APIRouter(
    prefix="/journal-entries",
    tags=["Journal Entries"],
)


def validate_journal_accounts(
    db: Session,
    company_id: int,
    payload: JournalEntryCreate | OpeningBalanceCreate,
):
    currencies: dict[str, int] = {}

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

        currencies.setdefault(account.currency, account.id)

    # One entry, one currency.
    #
    # An entry is valid when its debits equal its credits, and that comparison
    # is only meaningful inside a single unit: 500 riyals on one side and 500
    # dollars on the other balances arithmetically and means nothing. Allowing
    # it would put a number in the trial balance that is the sum of two
    # different things, which no later report could untangle.
    #
    # Moving value between currencies is a real operation with a rate and a
    # gain or loss, and this system does not model it yet. Until it does,
    # refusing is the honest answer -- a wrong number would be worse than a
    # blocked entry.
    if len(currencies) > 1:
        named = ", ".join(sorted(currencies))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"A journal entry cannot mix currencies. This one touches "
                f"{named}. Debits and credits only balance within one currency; "
                f"record a transfer between currencies as two entries, one in "
                f"each."
            ),
        )


# The unique index behind the duplicate-entry_no check below.
UNIQUE_ENTRY_NO_CONSTRAINT = "uq_journal_entries_company_entry_no"


def _is_duplicate_entry_no(exc: IntegrityError) -> bool:
    """Whether this violation is the duplicate entry_no and not some other one.

    journal_entries also carries four foreign keys, a status check and a second
    unique index. Mapping every IntegrityError to 409 would report any of them
    as "entry number already exists", so the constraint is identified by name.
    psycopg2 supplies it in diag; the string fallback is for a driver that does
    not, and anything unrecognised is re-raised rather than guessed at.
    """
    diagnostics = getattr(getattr(exc, "orig", None), "diag", None)
    name = getattr(diagnostics, "constraint_name", None)
    if name:
        return name == UNIQUE_ENTRY_NO_CONSTRAINT
    return UNIQUE_ENTRY_NO_CONSTRAINT in str(getattr(exc, "orig", None) or exc)


@router.post(
    "",
    response_model=JournalEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_journal_entry_endpoint(
    payload: JournalEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_company_or_none(db=db, company_id=payload.company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
        allowed_roles={"admin", "accountant"},
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

    command = CreateJournalEntryCommand(
        company_id=payload.company_id,
        fiscal_year_id=fiscal_year.id,
        fiscal_period_id=fiscal_period.id,
        entry_no=payload.entry_no,
        entry_date=payload.entry_date,
        description=payload.description,
        source_type=payload.source_type,
        source_id=payload.source_id,
        created_by_user_id=current_user.id,
        lines=tuple(
            CreateJournalLineCommand(
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
                description=line.description,
            )
            for line in payload.lines
        ),
    )
    repository = SqlAlchemyJournalRepository(db)
    # The get_journal_entry_by_no check above closes the ordinary case, but it
    # is a read followed by a write with no lock between them. Two requests
    # carrying the same entry_no both pass it, and the second one's flush hits
    # uq_journal_entries_company_entry_no. Without this the client got a 500 for
    # a conflict the endpoint already knows how to describe; the database was
    # never at risk, only the answer was wrong.
    try:
        journal_entry = CreateJournalEntry(repository).execute(command)
    except IntegrityError as exc:
        if not _is_duplicate_entry_no(exc):
            raise
        # SqlAlchemyJournalRepository.create already rolled the session back
        # before re-raising, so nothing is left to undo here.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Journal entry number already exists for this company",
        ) from exc

    prepare_audit_log(
        db=db,
        company_id=journal_entry.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="create_journal_entry",
        entity_type="journal_entry",
        entity_id=journal_entry.id,
        description=f"Created journal entry {journal_entry.entry_no}",
        new_values={
            "entry_no": journal_entry.entry_no,
            "status": journal_entry.status,
            "entry_date": str(journal_entry.entry_date),
        },
    )
    db.commit()

    return journal_entry


@router.post(
    "/opening-balance",
    response_model=JournalEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_opening_balance_endpoint(
    payload: OpeningBalanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_company_or_none(db=db, company_id=payload.company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
        allowed_roles={"admin", "accountant"},
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
            detail="No fiscal year found for this opening balance date",
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
            detail="No fiscal period found for this opening balance date",
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

    command = CreateOpeningBalanceCommand(
        company_id=payload.company_id,
        fiscal_year_id=fiscal_year.id,
        fiscal_period_id=fiscal_period.id,
        entry_no=payload.entry_no,
        entry_date=payload.entry_date,
        description=payload.description,
        created_by_user_id=current_user.id,
        lines=tuple(
            CreateJournalLineCommand(
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
                description=line.description,
            )
            for line in payload.lines
        ),
    )
    repository = SqlAlchemyJournalRepository(db)
    opening_entry = CreateOpeningBalance(repository).execute(command)

    prepare_audit_log(
        db=db,
        company_id=opening_entry.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="create_opening_balance",
        entity_type="journal_entry",
        entity_id=opening_entry.id,
        description=f"Created opening balance entry {opening_entry.entry_no}",
    )
    db.commit()

    return opening_entry


@router.get(
    "",
    response_model=PaginatedResponse[JournalEntryRead],
)
def list_journal_entries_endpoint(
    company_id: int = Query(..., ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )

    allowed_statuses = {"draft", "reviewed", "posted", "void", "reversed"}

    if status_filter is not None and status_filter not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid journal entry status",
        )

    repository = SqlAlchemyJournalRepository(db)
    result = ListJournalEntries(repository).execute(
        company_id=company_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )

    return PaginatedResponse[JournalEntryRead](
        items=result.items,
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.get(
    "/{journal_entry_id}",
    response_model=JournalEntryRead,
)
def get_journal_entry_endpoint(
    journal_entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = SqlAlchemyJournalRepository(db)
    journal_entry = GetJournalEntry(repository).execute(journal_entry_id)

    if not journal_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=journal_entry.company_id,
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
    current_user: User = Depends(get_current_user),
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

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=journal_entry.company_id,
        allowed_roles={"admin", "accountant"},
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

    update_data = payload.model_dump(exclude_unset=True)
    command = UpdateJournalEntryCommand(
        journal_entry_id=journal_entry_id,
        **update_data,
        fiscal_year_id=fiscal_year.id if fiscal_year is not None else None,
        fiscal_period_id=fiscal_period.id if fiscal_period is not None else None,
        fields=frozenset(update_data.keys()),
    )
    repository = SqlAlchemyJournalRepository(db)
    updated_entry = UpdateJournalEntry(repository).execute(command)

    prepare_audit_log(
        db=db,
        company_id=updated_entry.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="update_journal_entry",
        entity_type="journal_entry",
        entity_id=updated_entry.id,
        description=f"Updated draft journal entry {updated_entry.entry_no}",
        old_values={"status": "draft", "entry_no": updated_entry.entry_no},
        new_values={"status": "draft", "entry_no": updated_entry.entry_no},
    )
    db.commit()

    return updated_entry


@router.post(
    "/{journal_entry_id}/review",
    response_model=JournalEntryRead,
)
def review_journal_entry_endpoint(
    journal_entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=journal_entry.company_id,
        allowed_roles={"admin", "accountant", "reviewer"},
    )

    if journal_entry.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
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

    command = ReviewJournalEntryCommand(
        journal_entry_id=journal_entry_id,
    )
    repository = SqlAlchemyJournalRepository(db)
    reviewed_entry = ReviewJournalEntry(repository).execute(command)

    prepare_audit_log(
        db=db,
        company_id=reviewed_entry.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="review_journal_entry",
        entity_type="journal_entry",
        entity_id=reviewed_entry.id,
        description=f"Reviewed journal entry {reviewed_entry.entry_no}",
        old_values={"status": "draft"},
        new_values={"status": "reviewed"},
    )
    db.commit()

    return reviewed_entry


@router.post(
    "/{journal_entry_id}/post",
    response_model=JournalEntryRead,
)
def post_journal_entry_endpoint(
    journal_entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=journal_entry.company_id,
        allowed_roles={"admin", "approver"},
    )

    if journal_entry.status != "reviewed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only reviewed journal entries can be posted",
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

    command = PostJournalEntryCommand(
        journal_entry_id=journal_entry_id,
    )
    repository = SqlAlchemyJournalRepository(db)
    posted_entry = PostJournalEntry(repository).execute(command)

    prepare_audit_log(
        db=db,
        company_id=posted_entry.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="post_journal_entry",
        entity_type="journal_entry",
        entity_id=posted_entry.id,
        description=f"Posted journal entry {posted_entry.entry_no}",
        old_values={"status": "reviewed"},
        new_values={"status": "posted"},
    )
    db.commit()

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
    current_user: User = Depends(get_current_user),
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

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=original_entry.company_id,
        allowed_roles={"admin", "accountant", "approver"},
    )

    if original_entry.status != "posted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
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

    if get_reversal_for_entry(db=db, original_entry_id=original_entry.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Journal entry has already been reversed",
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

    command = ReverseJournalEntryCommand(
        original_entry_id=original_entry.id,
        fiscal_year_id=fiscal_year.id,
        fiscal_period_id=fiscal_period.id,
        entry_no=payload.entry_no,
        entry_date=payload.entry_date,
        description=payload.description,
        created_by_user_id=current_user.id,
    )
    repository = SqlAlchemyJournalRepository(db)
    reversal_entry = ReverseJournalEntry(repository).execute(command)

    prepare_audit_log(
        db=db,
        company_id=reversal_entry.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="reverse_journal_entry",
        entity_type="journal_entry",
        entity_id=reversal_entry.id,
        description=(
            f"Created reversal journal entry "
            f"{reversal_entry.entry_no} for {original_entry.entry_no}"
        ),
        old_values={"original_entry_no": original_entry.entry_no, "status": "posted"},
        new_values={"reversal_entry_no": reversal_entry.entry_no, "status": "posted"},
    )
    db.commit()

    return reversal_entry


@router.post(
    "/{journal_entry_id}/void",
    response_model=JournalEntryRead,
)
def void_journal_entry_endpoint(
    journal_entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=journal_entry.company_id,
        allowed_roles={"admin", "accountant"},
    )

    if journal_entry.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft journal entries can be voided",
        )

    command = VoidJournalEntryCommand(
        journal_entry_id=journal_entry_id,
    )
    repository = SqlAlchemyJournalRepository(db)
    voided_entry = VoidJournalEntry(repository).execute(command)

    prepare_audit_log(
        db=db,
        company_id=voided_entry.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="void_journal_entry",
        entity_type="journal_entry",
        entity_id=voided_entry.id,
        description=f"Voided draft journal entry {voided_entry.entry_no}",
        old_values={"status": "draft"},
        new_values={"status": "void"},
    )
    db.commit()

    return voided_entry
