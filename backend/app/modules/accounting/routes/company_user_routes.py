from fastapi import APIRouter, Depends, HTTPException, Query, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from sqlalchemy import func, select

from app.application.company_users.dto import CreateCompanyUserCommand, UpdateCompanyUserCommand
from app.application.company_users.use_cases import (
    CreateCompanyUser,
    GetCompanyUser,
    GetCompanyUserByCompanyAndUser,
    ListCompanyUsers,
    SetCompanyUserActive,
    UpdateCompanyUser,
)
from app.application.users.dto import SetUserActiveCommand
from app.application.users.use_cases import GetUser, SetUserActive
from app.core.auth_dependencies import get_current_user, get_current_user_optional
from app.core.company_access import ensure_company_access
from app.core.database import get_db
from app.core.pagination import PaginatedResponse
from app.infrastructure.database.sqlalchemy.repositories.company_user_repository import (
    SqlAlchemyCompanyUserRepository,
)
from app.infrastructure.database.sqlalchemy.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from app.modules.accounting.models.user import User
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.company_user_invitation import CompanyUserInvitation
from app.modules.accounting.schemas.company_user import (
    CompanyUserCreate,
    CompanyUserRead,
    CompanyUserUpdate,
)
from app.modules.accounting.schemas.user import UserRead
from app.modules.accounting.schemas.company_user_invitation import (
    CompanyUserInvitationCreate,
    CompanyUserInvitationResponse,
    CompanyUserInvitationValidateResponse,
    CompanyUserInvitationAccept,
    CompanyUserInvitationRead,
)
from app.application.invitations.errors import (
    ActiveInvitationExists,
    CompanyNotFound,
    EmailMismatch,
    InactiveCompany,
    InactiveMembershipExists,
    InvitationAlreadyAccepted,
    InvitationCancelled,
    InvitationConflict,
    InvitationExpired,
    InvitationInvalidToken,
    InvitationNotFound,
    MissingNewUserDetails,
    UserAlreadyMember,
    UserExistsLoginRequired,
)
from app.modules.accounting.services.company_user_invitation_service import (
    create_invitation,
    validate_invitation,
    accept_invitation,
    cancel_invitation,
    list_pending_invitations,
)
from app.modules.accounting.services.audit_service import prepare_audit_log


def _invitation_error_to_http(exc: Exception) -> HTTPException:
    """Convert a domain invitation error to an appropriate HTTPException."""
    if isinstance(exc, (InvitationInvalidToken,)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, InvitationAlreadyAccepted):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, (InvitationCancelled, InvitationExpired, InactiveCompany)):
        return HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc))
    if isinstance(exc, (ActiveInvitationExists, UserAlreadyMember, InactiveMembershipExists, InvitationConflict)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, (CompanyNotFound, InvitationNotFound)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, UserExistsLoginRequired):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    if isinstance(exc, EmailMismatch):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, MissingNewUserDetails):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    # Fallback
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _ensure_platform_superuser(current_user: User) -> None:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only a platform superuser can change global user account status',
        )


def _ensure_safe_global_deactivation(
    db: Session,
    current_user: User,
    target_user_id: int,
    target_is_superuser: bool,
    target_is_active: bool,
) -> None:
    if target_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='A platform superuser cannot deactivate their own account',
        )

    if not target_is_superuser or not target_is_active:
        return

    active_superuser_count = db.scalar(
        select(func.count()).select_from(User).where(
            User.is_active == True,  # noqa: E712
            User.is_superuser == True,  # noqa: E712
        )
    ) or 0
    if active_superuser_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot deactivate the final active platform superuser',
        )


# ── Module-level seam functions (monkeypatchable in unit tests) ───────────────


def get_user(db: Session, *, user_id: int):
    """Fetch a User ORM object by primary key.

    Defined at module level so unit tests can monkeypatch this symbol to inject
    fixture objects without needing a database connection.
    """
    return db.get(User, user_id)


def get_company_user(db: Session, *, company_user_id: int):
    """Fetch a CompanyUser ORM object by primary key.

    Defined at module level so unit tests can monkeypatch this symbol to inject
    fixture objects without needing a database connection.
    """
    return db.scalar(select(CompanyUser).where(CompanyUser.id == company_user_id))


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

    try:
        result = create_invitation(
            db=db,
            invitation_in=invitation_in,
            current_user=current_user,
        )
    except (
        ActiveInvitationExists, CompanyNotFound, InactiveMembershipExists,
        InvitationConflict, UserAlreadyMember,
    ) as exc:
        raise _invitation_error_to_http(exc) from exc
    db.commit()
    return result


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
    try:
        return validate_invitation(db=db, token=token)
    except (InvitationInvalidToken, InvitationAlreadyAccepted, InvitationCancelled, InvitationExpired) as exc:
        raise _invitation_error_to_http(exc) from exc


@router.post("/invitations/accept")
def accept_invitation_endpoint(
    payload: CompanyUserInvitationAccept,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    try:
        result = accept_invitation(
            db=db,
            payload=payload,
            current_user=current_user,
        )
    except (
        InvitationInvalidToken, InvitationAlreadyAccepted, InvitationCancelled,
        InvitationExpired, InactiveCompany, UserExistsLoginRequired, EmailMismatch,
        MissingNewUserDetails, InactiveMembershipExists, InvitationConflict,
    ) as exc:
        raise _invitation_error_to_http(exc) from exc
    db.commit()
    return result


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

    # Validate company exists
    from app.modules.accounting.models.company import Company
    from sqlalchemy import select as sa_select
    if not db.scalar(sa_select(Company).where(Company.id == payload.company_id)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    # Validate user exists
    user_repo = SqlAlchemyUserRepository(db)
    if user_repo.get(payload.user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    cu_repo = SqlAlchemyCompanyUserRepository(db)

    existing = GetCompanyUserByCompanyAndUser(cu_repo).execute(
        company_id=payload.company_id, user_id=payload.user_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already assigned to this company",
        )

    company_user = CreateCompanyUser(cu_repo).execute(
        CreateCompanyUserCommand(
            company_id=payload.company_id,
            user_id=payload.user_id,
            role=payload.role,
            is_active=payload.is_active,
        )
    )

    prepare_audit_log(
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
    db.commit()

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
    # Exempt from the subscription gate: the client resolves its own role from
    # this call, and it must still render the subscription-inactive screen.
    company_user = ensure_company_access(
        db=db,
        current_user=current_user,
        company_id=company_id,
        require_active_subscription=False,
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

    cu_repo = SqlAlchemyCompanyUserRepository(db)
    page = ListCompanyUsers(cu_repo).execute(
        company_id=company_id, user_id=user_id, skip=skip, limit=limit
    )

    return PaginatedResponse[CompanyUserRead](
        items=list(page.items),
        total=page.total,
        skip=page.skip,
        limit=page.limit,
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
    cu_repo = SqlAlchemyCompanyUserRepository(db)
    company_user = GetCompanyUser(cu_repo).execute(company_user_id)

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
    cu_repo = SqlAlchemyCompanyUserRepository(db)
    company_user = GetCompanyUser(cu_repo).execute(company_user_id)

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

    update_data = payload.model_dump(exclude_unset=True)
    updated = UpdateCompanyUser(cu_repo).execute(
        UpdateCompanyUserCommand(
            company_user_id=company_user_id,
            fields=frozenset(update_data.keys()),
            **update_data,
        )
    )

    prepare_audit_log(
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
    db.commit()

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
            CompanyUser.is_active == True,  # noqa: E712
        )
        admin_count = db.scalar(stmt) or 0
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote or remove the last active admin in the company.",
            )

    target_user = get_user(db=db, user_id=company_user.user_id)
    target_email = (target_user.email if target_user else None) or "Unknown"

    old_values = {"is_active": company_user.is_active}

    try:
        company_user.is_active = False
        db.add(company_user)
        prepare_audit_log(
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
            new_values={"is_active": False},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

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

    target = get_user(db=db, user_id=user_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    _ensure_safe_global_deactivation(
        db=db,
        current_user=current_user,
        target_user_id=target.id,
        target_is_superuser=target.is_superuser,
        target_is_active=target.is_active,
    )

    old_values = {
        "is_active": target.is_active,
        "target_user_id": target.id,
        "target_email": target.email,
        "target_name": target.full_name,
        "scope": "global",
    }

    try:
        target.is_active = False
        db.add(target)
        prepare_audit_log(
            db=db,
            company_id=None,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action="deactivate_user_account",
            entity_type="user",
            entity_id=target.id,
            description=f"Globally deactivated platform account for {target.email}",
            old_values=old_values,
            new_values={
                "is_active": False,
                "target_user_id": target.id,
                "target_email": target.email,
                "target_name": target.full_name,
                "scope": "global",
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return target


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_200_OK)
def cancel_invitation_endpoint(
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select as sa_select
    invite = db.execute(
        sa_select(CompanyUserInvitation).where(CompanyUserInvitation.id == invitation_id)
    ).scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    ensure_company_access(db, current_user, invite.company_id, allowed_roles=["admin"])

    try:
        cancel_invitation(
            db=db,
            invitation_id=invitation_id,
            current_user=current_user,
        )
    except (InvitationNotFound, InvitationAlreadyAccepted, InvitationCancelled, InvitationExpired) as exc:
        raise _invitation_error_to_http(exc) from exc
    db.commit()
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

    try:
        company_user.is_active = True
        db.add(company_user)
        prepare_audit_log(
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
            new_values={"is_active": True},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

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

    target = get_user(db=db, user_id=user_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    old_values = {
        "is_active": target.is_active,
        "target_user_id": target.id,
        "target_email": target.email,
        "target_name": target.full_name,
        "scope": "global",
    }

    try:
        target.is_active = True
        db.add(target)
        prepare_audit_log(
            db=db,
            company_id=None,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action="reactivate_user_account",
            entity_type="user",
            entity_id=target.id,
            description=f"Globally reactivated platform account for {target.email}",
            old_values=old_values,
            new_values={
                "is_active": True,
                "target_user_id": target.id,
                "target_email": target.email,
                "target_name": target.full_name,
                "scope": "global",
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return target
