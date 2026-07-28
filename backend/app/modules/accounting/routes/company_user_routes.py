from fastapi import APIRouter, Depends, HTTPException, Query, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from sqlalchemy import func, select

from app.core.auth_dependencies import get_current_user, get_current_user_optional
from app.core.company_access import ensure_company_access
from app.core.database import flush_or_rollback, get_db
from app.core.pagination import PaginatedResponse
from app.modules.accounting.models.user import User
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.company_user_invitation import CompanyUserInvitation
from app.modules.accounting.schemas.company_user import (
    CompanyUserCreate,
    CompanyUserRead,
    CompanyUserUpdate,
)
from app.modules.accounting.services.company_user_service import (
    count_company_users,
    create_company_user,
    get_company,
    get_company_user,
    get_company_user_by_company_and_user,
    get_user,
    list_company_users,
    update_company_user,
)
from app.modules.accounting.schemas.user import UserRead
from app.modules.accounting.schemas.company_user_invitation import (
    CompanyUserInvitationCreate,
    CompanyUserInvitationResponse,
    CompanyUserInvitationValidateResponse,
    CompanyUserInvitationAccept,
    CompanyUserInvitationRead,
)
from app.modules.accounting.services.company_user_invitation_service import (
    create_invitation,
    validate_invitation,
    accept_invitation,
    cancel_invitation,
    list_pending_invitations,
)
from app.modules.accounting.services.audit_service import create_atomic_audit_log


def _ensure_platform_superuser(current_user: User) -> None:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only a platform superuser can change global user account status',
        )


def _ensure_safe_global_deactivation(
    db: Session,
    current_user: User,
    target_user: User,
) -> None:
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='A platform superuser cannot deactivate their own account',
        )

    if not target_user.is_superuser or not target_user.is_active:
        return

    active_superuser_count = db.scalar(
        select(func.count()).select_from(User).where(
            User.is_superuser.is_(True),
            User.is_active.is_(True),
        )
    ) or 0
    if active_superuser_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot deactivate the final active platform superuser',
        )


router = APIRouter(
    prefix="/company-users",
    tags=["Company Users"],
)


@router.post("/invitations", response_model=CompanyUserInvitationResponse)
def create_invitation_endpoint(
    invitation_in: CompanyUserInvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyUserInvitationResponse:
    # Ensure current_user is an admin in the target company
    ensure_company_access(db, current_user, invitation_in.company_id, allowed_roles=["admin"])

    return create_invitation(
        db=db,
        invitation_in=invitation_in,
        current_user=current_user,
    )


@router.get("/invitations", response_model=list[CompanyUserInvitationRead])
def list_invitations_endpoint(
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CompanyUserInvitationRead]:
    ensure_company_access(db, current_user, company_id, allowed_roles=["admin"])
    return list_pending_invitations(db=db, company_id=company_id)


@router.get("/invitations/validate", response_model=CompanyUserInvitationValidateResponse)
def validate_invitation_endpoint(
    token: str = Query(...),
    db: Session = Depends(get_db),
) -> CompanyUserInvitationValidateResponse:
    return validate_invitation(db=db, token=token)


@router.post("/invitations/accept")
def accept_invitation_endpoint(
    payload: CompanyUserInvitationAccept,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    return accept_invitation(
        db=db,
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "",
    response_model=CompanyUserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_company_user_endpoint(
    payload: CompanyUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=payload.company_id,
        allowed_roles={"admin"},
    )

    company = get_company(db=db, company_id=payload.company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    user = get_user(db=db, user_id=payload.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    existing_company_user = get_company_user_by_company_and_user(
        db=db,
        company_id=payload.company_id,
        user_id=payload.user_id,
    )

    if existing_company_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already assigned to this company",
        )

    company_user = create_company_user(
        db=db,
        payload=payload,
    )

    create_atomic_audit_log(
        db=db,
        company_id=company_user.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="create_company_user",
        entity_type="company_user",
        entity_id=company_user.id,
        description=f"Added user {payload.user_id} to company {payload.company_id} with role {company_user.role}",
    )

    return company_user


@router.get(
    "/me",
    response_model=CompanyUserRead,
)
def get_my_company_user_endpoint(
    company_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyUser:
    company_user = ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
    )
    return company_user


@router.get(
    "",
    response_model=PaginatedResponse[CompanyUserRead],
)
def list_company_users_endpoint(
    company_id: int = Query(..., ge=1),
    user_id: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
        allowed_roles={"admin", "auditor"},
    )

    company_users = list_company_users(
        db=db,
        company_id=company_id,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )

    total = count_company_users(
        db=db,
        company_id=company_id,
        user_id=user_id,
    )

    return PaginatedResponse[CompanyUserRead](
        items=company_users,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{company_user_id}",
    response_model=CompanyUserRead,
)
def get_company_user_endpoint(
    company_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_user = get_company_user(
        db=db,
        company_user_id=company_user_id,
    )

    if not company_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company user not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_user.company_id,
        allowed_roles={"admin", "auditor"},
    )

    return company_user


@router.patch(
    "/{company_user_id}",
    response_model=CompanyUserRead,
)
def update_company_user_endpoint(
    company_user_id: int,
    payload: CompanyUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_user = get_company_user(
        db=db,
        company_user_id=company_user_id,
    )

    if not company_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company user not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_user.company_id,
        allowed_roles={"admin"},
    )

    # Prevent the last active admin from removing or demoting themselves
    if company_user.user_id == current_user.id and company_user.role == "admin":
        is_demoting = payload.role is not None and payload.role != "admin"
        is_removing = payload.is_active is not None and not payload.is_active

        if is_demoting or is_removing:
            stmt = select(func.count()).select_from(CompanyUser).where(
                CompanyUser.company_id == company_user.company_id,
                CompanyUser.role == "admin",
                CompanyUser.is_active == True,
            )
            admin_count = db.scalar(stmt) or 0

            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote or remove the only admin in the company.",
                )

    old_role = company_user.role
    old_is_active = company_user.is_active

    updated = update_company_user(
        db=db,
        company_user=company_user,
        payload=payload,
    )

    create_atomic_audit_log(
        db=db,
        company_id=updated.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="update_company_user",
        entity_type="company_user",
        entity_id=updated.id,
        description=f"Updated company user {updated.id} in company {updated.company_id}",
        old_values={"role": old_role, "is_active": old_is_active},
        new_values={"role": updated.role, "is_active": updated.is_active},
    )

    return updated


@router.patch("/{company_user_id}/remove-access", response_model=CompanyUserRead)
def remove_company_access_endpoint(
    company_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_user = get_company_user(db=db, company_user_id=company_user_id)
    if not company_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company user not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_user.company_id,
        allowed_roles={"admin"},
    )

    if company_user.role == "admin" and company_user.is_active:
        stmt = select(func.count()).select_from(CompanyUser).where(
            CompanyUser.company_id == company_user.company_id,
            CompanyUser.role == "admin",
            CompanyUser.is_active == True,
        )
        admin_count = db.scalar(stmt) or 0
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote or remove the last active admin in the company.",
            )

    old_values = {"is_active": company_user.is_active}
    company_user.is_active = False
    db.add(company_user)
    flush_or_rollback(db)

    new_values = {"is_active": False}

    target_user = get_user(db=db, user_id=company_user.user_id)
    target_email = target_user.email if target_user else "Unknown"

    create_atomic_audit_log(
        db=db,
        company_id=company_user.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="remove_company_access",
        entity_type="company_user",
        entity_id=company_user.id,
        description=f"Removed company access for user {target_email} in company {company_user.company_id}",
        old_values=old_values,
        new_values=new_values,
    )

    return company_user


@router.patch("/users/{user_id}/deactivate", response_model=UserRead)
def deactivate_user_account_endpoint(
    user_id: int,
    company_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    '''Globally deactivate a platform account; company_id is retained for API compatibility.'''
    _ensure_platform_superuser(current_user)

    target_user = get_user(db=db, user_id=user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    _ensure_safe_global_deactivation(
        db=db,
        current_user=current_user,
        target_user=target_user,
    )

    old_values = {
        "is_active": target_user.is_active,
        "target_user_id": target_user.id,
        "target_email": target_user.email,
        "target_name": target_user.full_name,
        "scope": "global",
    }
    target_user.is_active = False
    db.add(target_user)
    flush_or_rollback(db)

    new_values = {
        "is_active": False,
        "target_user_id": target_user.id,
        "target_email": target_user.email,
        "target_name": target_user.full_name,
        "scope": "global",
    }

    create_atomic_audit_log(
        db=db,
        company_id=None,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="deactivate_user_account",
        entity_type="user",
        entity_id=target_user.id,
        description=f"Globally deactivated platform account for {target_user.email}",
        old_values=old_values,
        new_values=new_values,
    )

    return target_user


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_200_OK)
def cancel_invitation_endpoint(
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invite = db.execute(
        select(CompanyUserInvitation).where(CompanyUserInvitation.id == invitation_id)
    ).scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    ensure_company_access(db, current_user, invite.company_id, allowed_roles=["admin"])

    cancel_invitation(
        db=db,
        invitation_id=invitation_id,
        current_user=current_user,
    )

    return {"status": "success", "message": "Invitation cancelled successfully"}


@router.patch("/{company_user_id}/restore-access", response_model=CompanyUserRead)
def restore_company_access_endpoint(
    company_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_user = get_company_user(db=db, company_user_id=company_user_id)
    if not company_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company user not found",
        )

    ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_user.company_id,
        allowed_roles={"admin"},
    )

    target_user = get_user(db=db, user_id=company_user.user_id)
    if not target_user or not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account is deactivated. Reactivate account first.",
        )

    old_values = {"is_active": company_user.is_active}
    company_user.is_active = True
    db.add(company_user)
    flush_or_rollback(db)

    new_values = {"is_active": True}

    create_atomic_audit_log(
        db=db,
        company_id=company_user.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="restore_company_access",
        entity_type="company_user",
        entity_id=company_user.id,
        description=f"Restored company access for user {target_user.email} in company {company_user.company_id}",
        old_values=old_values,
        new_values=new_values,
    )

    return company_user


@router.patch("/users/{user_id}/reactivate", response_model=UserRead)
def reactivate_user_account_endpoint(
    user_id: int,
    company_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    '''Globally reactivate a platform account; company_id is retained for API compatibility.'''
    _ensure_platform_superuser(current_user)

    target_user = get_user(db=db, user_id=user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    old_values = {
        "is_active": target_user.is_active,
        "target_user_id": target_user.id,
        "target_email": target_user.email,
        "target_name": target_user.full_name,
        "scope": "global",
    }
    target_user.is_active = True
    db.add(target_user)
    flush_or_rollback(db)

    new_values = {
        "is_active": True,
        "target_user_id": target_user.id,
        "target_email": target_user.email,
        "target_name": target_user.full_name,
        "scope": "global",
    }

    create_atomic_audit_log(
        db=db,
        company_id=None,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="reactivate_user_account",
        entity_type="user",
        entity_id=target_user.id,
        description=f"Globally reactivated platform account for {target_user.email}",
        old_values=old_values,
        new_values=new_values,
    )

    return target_user
