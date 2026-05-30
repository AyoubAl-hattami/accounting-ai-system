from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.core.pagination import PaginatedResponse
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.account import (
    AccountCreate,
    AccountRead,
    AccountSeedResult,
    AccountUpdate,
)
from app.modules.accounting.services.account_service import (
    count_accounts,
    create_account,
    get_account,
    get_account_by_code,
    get_company_or_none,
    list_accounts,
    update_account,
)
from app.modules.accounting.services.default_accounts_service import (
    seed_default_accounts,
)
from app.modules.accounting.services.audit_service import create_audit_log


router = APIRouter(
    prefix="/accounts",
    tags=["Accounts"],
)


@router.post(
    "",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
)
def create_account_endpoint(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
        allowed_roles={"admin", "accountant"},
    )

    if payload.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System accounts can only be created by the default account seed",
        )

    company = get_company_or_none(db=db, company_id=payload.company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    existing_account = get_account_by_code(
        db=db,
        company_id=payload.company_id,
        code=payload.code.strip(),
    )

    if existing_account:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account code already exists for this company",
        )

    if payload.parent_id is not None:
        parent_account = get_account(db=db, account_id=payload.parent_id)

        if not parent_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent account not found",
            )

        if parent_account.company_id != payload.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent account must belong to the same company",
            )

    account = create_account(db=db, payload=payload)

    create_audit_log(
        db=db,
        company_id=account.company_id,
        actor=current_user.email,
        action="create_account",
        entity_type="account",
        entity_id=account.id,
        description=f"Created account {account.code} - {account.name}",
    )

    return account


@router.get(
    "",
    response_model=PaginatedResponse[AccountRead],
)
def list_accounts_endpoint(
    company_id: int = Query(..., ge=1),
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

    accounts = list_accounts(
        db=db,
        company_id=company_id,
        skip=skip,
        limit=limit,
    )

    total = count_accounts(
        db=db,
        company_id=company_id,
    )

    return PaginatedResponse[AccountRead](
        items=accounts,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/seed-defaults",
    response_model=AccountSeedResult,
)
def seed_default_accounts_endpoint(
    company_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
        allowed_roles={"admin", "accountant"},
    )

    result = seed_default_accounts(
        db=db,
        company_id=company_id,
    )

    create_audit_log(
        db=db,
        company_id=company_id,
        actor=current_user.email,
        action="seed_default_accounts",
        entity_type="account",
        entity_id=None,
        description=(
            f"Seeded default accounts: "
            f"{result.created_count} created, {result.skipped_count} skipped"
        ),
    )

    return result


@router.get(
    "/{account_id}",
    response_model=AccountRead,
)
def get_account_endpoint(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = get_account(db=db, account_id=account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=account.company_id,
    )

    return account


@router.patch(
    "/{account_id}",
    response_model=AccountRead,
)
def update_account_endpoint(
    account_id: int,
    payload: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = get_account(db=db, account_id=account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=account.company_id,
        allowed_roles={"admin", "accountant"},
    )

    if account.is_system:
        update_data = payload.model_dump(exclude_unset=True)

        protected_fields = {
            "code",
            "account_type",
            "parent_id",
            "is_system",
            "is_active",
        }

        attempted_protected_changes = protected_fields.intersection(update_data.keys())

        if attempted_protected_changes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "System accounts cannot update protected fields: "
                    + ", ".join(sorted(attempted_protected_changes))
                ),
            )

    if payload.code is not None:
        existing_account = get_account_by_code(
            db=db,
            company_id=account.company_id,
            code=payload.code.strip(),
        )

        if existing_account and existing_account.id != account.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account code already exists for this company",
            )

    if payload.parent_id is not None:
        if payload.parent_id == account.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account cannot be its own parent",
            )

        parent_account = get_account(db=db, account_id=payload.parent_id)

        if not parent_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent account not found",
            )

        if parent_account.company_id != account.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent account must belong to the same company",
            )

    updated = update_account(db=db, account=account, payload=payload)

    create_audit_log(
        db=db,
        company_id=updated.company_id,
        actor=current_user.email,
        action="update_account",
        entity_type="account",
        entity_id=updated.id,
        description=f"Updated account {updated.code} - {updated.name}",
    )

    return updated