import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.company_user_invitation import CompanyUserInvitation
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.company_user_invitation import (
    CompanyUserInvitationAccept,
    CompanyUserInvitationCreate,
    CompanyUserInvitationResponse,
    CompanyUserInvitationValidateResponse,
)
from app.modules.accounting.services.audit_service import create_audit_log


def create_invitation(
    db: Session,
    invitation_in: CompanyUserInvitationCreate,
    current_user: User,
) -> CompanyUserInvitationResponse:
    # Check if company exists
    company = db.execute(select(Company).where(Company.id == invitation_in.company_id)).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    # Check if user already exists
    existing_user = db.execute(select(User).where(User.email == invitation_in.email)).scalar_one_or_none()

    if existing_user:
        # Check if they are already in the company
        existing_company_user = db.execute(
            select(CompanyUser).where(
                CompanyUser.user_id == existing_user.id,
                CompanyUser.company_id == invitation_in.company_id
            )
        ).scalar_one_or_none()

        if existing_company_user:
            return CompanyUserInvitationResponse(
                status="error",
                message="User is already a member of this company"
            )

        # Add them directly
        new_cu = CompanyUser(
            company_id=invitation_in.company_id,
            user_id=existing_user.id,
            role=invitation_in.role,
            is_active=True,
        )
        db.add(new_cu)
        db.commit()

        create_audit_log(
            db=db,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action="ADD_COMPANY_USER_DIRECT",
            entity_type="COMPANY_USER",
            entity_id=new_cu.id,
            company_id=invitation_in.company_id,
            description=f"Added {invitation_in.email} directly",
        )

        return CompanyUserInvitationResponse(
            status="added_existing",
            message="User already had an account and was added directly.",
        )

    # Check for active existing invitations
    active_invites = db.execute(
        select(CompanyUserInvitation).where(
            CompanyUserInvitation.email == invitation_in.email,
            CompanyUserInvitation.company_id == invitation_in.company_id,
            CompanyUserInvitation.accepted_at.is_(None),
            CompanyUserInvitation.expires_at > datetime.now(timezone.utc),
        )
    ).scalars().all()

    if active_invites:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active invitation already exists for this email and company."
        )

    # Generate token
    raw_token = secrets.token_urlsafe(32)
    hashed_token = hash_password(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    new_invite = CompanyUserInvitation(
        company_id=invitation_in.company_id,
        email=invitation_in.email,
        role=invitation_in.role,
        token_hash=hashed_token,
        expires_at=expires_at,
        invited_by_user_id=current_user.id,
    )
    db.add(new_invite)
    db.commit()
    db.refresh(new_invite)
    
    full_token = f"{new_invite.id}:{raw_token}"

    create_audit_log(
        db=db,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="CREATE_INVITATION",
        entity_type="INVITATION",
        entity_id=new_invite.id,
        company_id=invitation_in.company_id,
        description=f"Invited {invitation_in.email}",
    )

    return CompanyUserInvitationResponse(
        status="invited",
        message="Invitation created successfully.",
        token=full_token,
        invite_url=f"/accept-invite?token={full_token}"
    )


def validate_invitation(db: Session, token: str) -> CompanyUserInvitationValidateResponse:
    try:
        invite_id_str, raw_token = token.split(":", 1)
        invite_id = int(invite_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token format.")

    invite = db.execute(select(CompanyUserInvitation).where(CompanyUserInvitation.id == invite_id)).scalar_one_or_none()
    
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")
        
    if not verify_password(raw_token, invite.token_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token.")
        
    if invite.accepted_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has already been accepted.")
        
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired.")
        
    company = db.execute(select(Company).where(Company.id == invite.company_id)).scalar_one_or_none()
    existing_user = db.execute(select(User).where(User.email == invite.email)).scalar_one_or_none()
    
    return CompanyUserInvitationValidateResponse(
        valid=True,
        email=invite.email,
        role=invite.role,
        company_name=company.name if company else "Unknown Company",
        user_exists=existing_user is not None
    )


def accept_invitation(
    db: Session,
    payload: CompanyUserInvitationAccept,
    current_user: User | None = None,
) -> dict:
    try:
        invite_id_str, raw_token = payload.token.split(":", 1)
        invite_id = int(invite_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token format.")

    invite = db.execute(select(CompanyUserInvitation).where(CompanyUserInvitation.id == invite_id)).scalar_one_or_none()
    
    if not invite or not verify_password(raw_token, invite.token_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token.")
        
    if invite.accepted_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation already accepted.")
        
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation expired.")
        
    existing_user = db.execute(select(User).where(User.email == invite.email)).scalar_one_or_none()
    
    user_to_add = None
    
    if existing_user:
        # Existing user path
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User exists. Please log in to accept this invitation."
            )
        if current_user.email != invite.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Logged in user email does not match invitation email."
            )
        user_to_add = current_user
    else:
        # New user path
        if not payload.password or not payload.full_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password and full name are required for new users."
            )
            
        hashed_pw = hash_password(payload.password)
        new_user = User(
            email=invite.email,
            full_name=payload.full_name,
            hashed_password=hashed_pw,
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user_to_add = new_user

    # Check if they are already in the company (just in case)
    existing_company_user = db.execute(
        select(CompanyUser).where(
            CompanyUser.user_id == user_to_add.id,
            CompanyUser.company_id == invite.company_id
        )
    ).scalar_one_or_none()

    if existing_company_user:
        # Already in company, just mark accepted
        invite.accepted_at = datetime.now(timezone.utc)
        invite.accepted_by_user_id = user_to_add.id
        db.commit()
        return {"status": "success", "message": "Already a member."}

    # Add to company
    new_cu = CompanyUser(
        company_id=invite.company_id,
        user_id=user_to_add.id,
        role=invite.role,
        is_active=True,
    )
    db.add(new_cu)
    
    invite.accepted_at = datetime.now(timezone.utc)
    invite.accepted_by_user_id = user_to_add.id
    
    db.commit()
    
    create_audit_log(
        db=db,
        actor=user_to_add.email,
        actor_user_id=user_to_add.id,
        actor_email=user_to_add.email,
        actor_name=user_to_add.full_name,
        action="ACCEPT_INVITATION",
        entity_type="INVITATION",
        entity_id=invite.id,
        company_id=invite.company_id,
        description="Invitation accepted",
    )

    return {"status": "success", "message": "Invitation accepted successfully."}


def list_pending_invitations(
    db: Session,
    company_id: int,
) -> list[CompanyUserInvitation]:
    return list(
        db.execute(
            select(CompanyUserInvitation).where(
                CompanyUserInvitation.company_id == company_id,
                CompanyUserInvitation.accepted_at.is_(None),
                CompanyUserInvitation.expires_at > datetime.now(timezone.utc),
            )
        ).scalars().all()
    )
