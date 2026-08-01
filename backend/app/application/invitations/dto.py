"""Framework-neutral DTOs for the invitation bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class InvitationResultDTO:
    """Result of a create-invitation or accept-invitation operation."""

    status: str
    message: str
    invite_url: str | None = None
    token: str | None = None


@dataclass(frozen=True, slots=True)
class InvitationValidationDTO:
    """Result of validating an invitation token."""

    valid: bool
    email: str
    role: str
    company_name: str
    user_exists: bool


@dataclass(frozen=True, slots=True)
class InvitationDTO:
    """Read projection of a persisted invitation record."""

    id: int
    company_id: int
    email: str
    role: str
    invited_by_user_id: int
    expires_at: datetime
    created_at: datetime
    status: str
    accepted_at: datetime | None = None
    accepted_by_user_id: int | None = None
    cancelled_at: datetime | None = None
    cancelled_by_user_id: int | None = None


@dataclass(frozen=True, slots=True)
class CreateInvitationCommand:
    company_id: int
    email: str
    role: str
    invited_by_user_id: int
    invited_by_email: str
    invited_by_name: str | None = None


@dataclass(frozen=True, slots=True)
class AcceptInvitationCommand:
    token: str
    current_user_id: int | None = None
    current_user_email: str | None = None
    full_name: str | None = None
    password: str | None = None
