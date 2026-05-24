from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.accounting.schemas.account import (
    AccountCreate,
    AccountRead,
    AccountUpdate,
)
from app.modules.accounting.services.account_service import (
    create_account,
    get_account,
    get_account_by_code,
    get_company_or_none,
    list_accounts,
    update_account,
)


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
):
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

    return create_account(db=db, payload=payload)


@router.get(
    "",
    response_model=list[AccountRead],
)
def list_accounts_endpoint(
    company_id: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_accounts(
        db=db,
        company_id=company_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{account_id}",
    response_model=AccountRead,
)
def get_account_endpoint(
    account_id: int,
    db: Session = Depends(get_db),
):
    account = get_account(db=db, account_id=account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
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
):
    account = get_account(db=db, account_id=account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
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

    return update_account(db=db, account=account, payload=payload)