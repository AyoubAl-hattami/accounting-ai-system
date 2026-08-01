"""Company-user invitation service.

.. deprecated::
    Direct imports of this service from routes are being phased out.
    Callers should use the application use-cases in
    ``app.application.invitations`` instead (Phase 39 migration target).
    This module no longer imports FastAPI — all domain errors are raised
    as exceptions from ``app.application.invitations.errors``.
"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.invitations.dto import (
    AcceptInvitationCommand,
    CreateInvitationCommand,
    InvitationDTO,
    InvitationResultDTO,
    InvitationValidationDTO,
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
from app.core.database import flush_or_rollback
from app.core.identity import normalize_email
from app.core.security import hash_password, verify_password
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.company_user_invitation import CompanyUserInvitation
from app.modules.accounting.models.user import User
from app.modules.accounting.services.audit_service import prepare_audit_log


def _parse_token(token: str) -> tuple[int, str]:
    try:
        invite_id_raw, raw_token = token.split(":", 1)
        return int(invite_id_raw), raw_token
    except ValueError:
        raise InvitationInvalidToken("Invalid token format.")


def _is_expired(invite: CompanyUserInvitation) -> bool:
    expires_at = invite.expires_at
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)
    return expires_at < now


def _get_invitation_by_token(
    db: Session,
    token: str,
    *,
    lock: bool,
) -> CompanyUserInvitation:
    invite_id, raw_token = _parse_token(token)
    statement = select(CompanyUserInvitation).where(
        CompanyUserInvitation.id == invite_id
    )
    if lock:
        statement = statement.with_for_update().execution_options(
            populate_existing=True
        )
    invite = db.scalar(statement)
    if not invite or not verify_password(raw_token, invite.token_hash):
        raise InvitationInvalidToken("Invalid invitation token.")
    return invite


def _ensure_pending(invite: CompanyUserInvitation) -> None:
    if invite.accepted_at is not None:
        raise InvitationAlreadyAccepted("Invitation has already been accepted.")
    if invite.cancelled_at is not None:
        raise InvitationCancelled("Invitation has been cancelled.")
    if _is_expired(invite):
        raise InvitationExpired("Invitation has expired.")


def _normalized_user_statement(normalized_email: str):
    return select(User).where(
        func.lower(func.trim(User.email)) == normalized_email
    )


def _to_invitation_dto(invite: CompanyUserInvitation) -> InvitationDTO:
    return InvitationDTO(
        id=invite.id,
        company_id=invite.company_id,
        email=invite.email,
        role=invite.role,
        invited_by_user_id=invite.invited_by_user_id,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
        status=invite.status,
        accepted_at=invite.accepted_at,
        accepted_by_user_id=invite.accepted_by_user_id,
        cancelled_at=invite.cancelled_at,
        cancelled_by_user_id=invite.cancelled_by_user_id,
    )


def create_invitation(
    db: Session,
    invitation_in,
    current_user: User,
) -> InvitationResultDTO:
    normalized_email = normalize_email(str(invitation_in.email))
    company = db.scalar(
        select(Company).where(Company.id == invitation_in.company_id)
    )
    if not company:
        raise CompanyNotFound("Company not found")

    existing_user = db.scalar(_normalized_user_statement(normalized_email))
    if existing_user:
        existing_membership = db.scalar(
            select(CompanyUser).where(
                CompanyUser.user_id == existing_user.id,
                CompanyUser.company_id == invitation_in.company_id,
            ).with_for_update()
        )
        if existing_membership:
            if not existing_membership.is_active:
                raise InactiveMembershipExists(
                    "User already has an inactive membership in this company. "
                    "Restore company access instead."
                )
            raise UserAlreadyMember("User is already a member of this company")

        membership = CompanyUser(
            company_id=invitation_in.company_id,
            user_id=existing_user.id,
            role=invitation_in.role,
            is_active=True,
        )
        db.add(membership)
        try:
            flush_or_rollback(db)
        except IntegrityError:
            raise InvitationConflict("User is already assigned to this company.")

        prepare_audit_log(
            db=db,
            actor=current_user.email,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_name=current_user.full_name,
            action="add_company_user_direct",
            entity_type="company_user",
            entity_id=membership.id,
            company_id=invitation_in.company_id,
            description=f"Added {normalized_email} directly",
            new_values={
                "role": invitation_in.role,
                "email": normalized_email,
            },
        )
        return InvitationResultDTO(
            status="added_existing",
            message="User already had an account and was added directly.",
        )

    now = datetime.now(timezone.utc)
    live_invitations = list(
        db.scalars(
            select(CompanyUserInvitation).where(
                CompanyUserInvitation.company_id == invitation_in.company_id,
                CompanyUserInvitation.normalized_email == normalized_email,
                CompanyUserInvitation.accepted_at.is_(None),
                CompanyUserInvitation.cancelled_at.is_(None),
            ).with_for_update()
        ).all()
    )
    superseded_ids: list[int] = []
    for existing_invite in live_invitations:
        if not _is_expired(existing_invite):
            raise ActiveInvitationExists(
                "An active invitation already exists for this email and company."
            )
        existing_invite.cancelled_at = now
        existing_invite.cancelled_by_user_id = current_user.id
        superseded_ids.append(existing_invite.id)
        db.add(existing_invite)

    raw_token = secrets.token_urlsafe(32)
    invite = CompanyUserInvitation(
        company_id=invitation_in.company_id,
        email=normalized_email,
        normalized_email=normalized_email,
        role=invitation_in.role,
        token_hash=hash_password(raw_token),
        expires_at=now + timedelta(days=7),
        invited_by_user_id=current_user.id,
    )
    db.add(invite)
    try:
        flush_or_rollback(db)
    except IntegrityError:
        raise ActiveInvitationExists(
            "An active invitation already exists for this email and company."
        )

    full_token = f"{invite.id}:{raw_token}"
    prepare_audit_log(
        db=db,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="create_invitation",
        entity_type="invitation",
        entity_id=invite.id,
        company_id=invitation_in.company_id,
        description=f"Invited {normalized_email}",
        new_values={
            "email": normalized_email,
            "role": invitation_in.role,
            "expires_at": invite.expires_at.isoformat(),
            "status": "pending",
            "superseded_expired_invitation_ids": superseded_ids,
        },
    )
    return InvitationResultDTO(
        status="invited",
        message="Invitation created successfully.",
        token=full_token,
        invite_url=f"/accept-invite?token={full_token}",
    )


def validate_invitation(
    db: Session,
    token: str,
) -> InvitationValidationDTO:
    invite = _get_invitation_by_token(db, token, lock=False)
    _ensure_pending(invite)
    company = db.scalar(select(Company).where(Company.id == invite.company_id))
    existing_user = db.scalar(
        _normalized_user_statement(invite.normalized_email)
    )
    return InvitationValidationDTO(
        valid=True,
        email=invite.email,
        role=invite.role,
        company_name=company.name if company else "Unknown Company",
        user_exists=existing_user is not None,
    )


def accept_invitation(
    db: Session,
    payload,
    current_user: User | None = None,
) -> dict:
    invite = _get_invitation_by_token(db, payload.token, lock=True)
    _ensure_pending(invite)
    company = db.scalar(
        select(Company).where(Company.id == invite.company_id).with_for_update()
    )
    if not company or not company.is_active:
        raise InactiveCompany("Invitation company is not active.")

    existing_user = db.scalar(
        _normalized_user_statement(invite.normalized_email).with_for_update()
    )
    if existing_user:
        if not current_user:
            raise UserExistsLoginRequired(
                "User exists. Please log in to accept this invitation."
            )
        if normalize_email(current_user.email) != invite.normalized_email:
            raise EmailMismatch(
                "Logged in user email does not match invitation email."
            )
        user_to_add = existing_user
    else:
        if not payload.password or not payload.full_name:
            raise MissingNewUserDetails(
                "Password and full name are required for new users."
            )
        user_to_add = User(
            email=invite.normalized_email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            is_active=True,
            is_superuser=False,
        )
        db.add(user_to_add)
        try:
            flush_or_rollback(db)
        except IntegrityError:
            raise InvitationConflict(
                "An account for this email was created concurrently. "
                "Log in to accept the invitation."
            )

    membership = db.scalar(
        select(CompanyUser).where(
            CompanyUser.user_id == user_to_add.id,
            CompanyUser.company_id == invite.company_id,
        ).with_for_update()
    )
    membership_existed = membership is not None
    if membership and not membership.is_active:
        raise InactiveMembershipExists(
            "An inactive company membership already exists. "
            "A company administrator must restore access."
        )
    if membership is None:
        membership = CompanyUser(
            company_id=invite.company_id,
            user_id=user_to_add.id,
            role=invite.role,
            is_active=True,
        )
        db.add(membership)

    accepted_at = datetime.now(timezone.utc)
    invite.accepted_at = accepted_at
    invite.accepted_by_user_id = user_to_add.id
    db.add(invite)
    try:
        flush_or_rollback(db)
    except IntegrityError:
        raise InvitationConflict("Invitation acceptance conflicted with another request.")

    prepare_audit_log(
        db=db,
        actor=user_to_add.email,
        actor_user_id=user_to_add.id,
        actor_email=user_to_add.email,
        actor_name=user_to_add.full_name,
        action="accept_invitation",
        entity_type="invitation",
        entity_id=invite.id,
        company_id=invite.company_id,
        description="Invitation accepted",
        old_values={
            "status": "pending",
            "email": invite.normalized_email,
            "role": invite.role,
        },
        new_values={
            "status": "accepted",
            "accepted_at": accepted_at.isoformat(),
            "user_id": user_to_add.id,
            "company_user_id": membership.id,
            "email": invite.normalized_email,
            "role": invite.role,
        },
    )
    message = (
        "Already a member. Invitation marked accepted."
        if membership_existed
        else "Invitation accepted successfully."
    )
    return {"status": "success", "message": message}


def cancel_invitation(
    db: Session,
    invitation_id: int,
    current_user: User,
) -> InvitationDTO:
    invite = db.scalar(
        select(CompanyUserInvitation).where(
            CompanyUserInvitation.id == invitation_id
        ).with_for_update().execution_options(
            populate_existing=True
        )
    )
    if not invite:
        raise InvitationNotFound("Invitation not found")
    _ensure_pending(invite)
    cancelled_at = datetime.now(timezone.utc)
    invite.cancelled_at = cancelled_at
    invite.cancelled_by_user_id = current_user.id
    db.add(invite)
    flush_or_rollback(db)
    prepare_audit_log(
        db=db,
        company_id=invite.company_id,
        actor=current_user.email,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_name=current_user.full_name,
        action="cancel_invitation",
        entity_type="invitation",
        entity_id=invite.id,
        description=f"Cancelled invitation for {invite.normalized_email}",
        old_values={
            "status": "pending",
            "email": invite.normalized_email,
            "role": invite.role,
            "expires_at": invite.expires_at.isoformat(),
        },
        new_values={
            "status": "cancelled",
            "cancelled_at": cancelled_at.isoformat(),
            "cancelled_by_user_id": current_user.id,
        },
    )
    return _to_invitation_dto(invite)


def list_pending_invitations(
    db: Session,
    company_id: int,
) -> list[InvitationDTO]:
    invites = list(
        db.scalars(
            select(CompanyUserInvitation).where(
                CompanyUserInvitation.company_id == company_id,
                CompanyUserInvitation.accepted_at.is_(None),
                CompanyUserInvitation.cancelled_at.is_(None),
                CompanyUserInvitation.expires_at > datetime.now(timezone.utc),
            )
        ).all()
    )
    return [_to_invitation_dto(inv) for inv in invites]
