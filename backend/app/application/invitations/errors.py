"""Domain exceptions for the invitation bounded context.

These are framework-neutral.  Callers in the interface layer (routes) catch
them and convert to appropriate HTTP responses.
"""

from __future__ import annotations


class InvitationError(Exception):
    """Base for all invitation domain errors."""


class InvitationNotFound(InvitationError):
    """No invitation exists with the requested identifier."""


class InvitationInvalidToken(InvitationError):
    """Token format is malformed or does not match the stored hash."""


class InvitationAlreadyAccepted(InvitationError):
    """Invitation has already been accepted."""


class InvitationCancelled(InvitationError):
    """Invitation has been cancelled."""


class InvitationExpired(InvitationError):
    """Invitation has passed its expiry date."""


class ActiveInvitationExists(InvitationError):
    """A live, non-expired invitation already exists for this email+company."""


class CompanyNotFound(InvitationError):
    """Referenced company does not exist."""


class InactiveCompany(InvitationError):
    """Invitation company is not active."""


class UserAlreadyMember(InvitationError):
    """User is already an active member of the company."""


class InactiveMembershipExists(InvitationError):
    """User has an inactive membership; admin must restore access instead."""


class UserExistsLoginRequired(InvitationError):
    """An account for this email already exists; the user must log in to accept."""


class EmailMismatch(InvitationError):
    """Logged-in user email does not match the invitation email."""


class MissingNewUserDetails(InvitationError):
    """Password and full name are required when creating a new account via invitation."""


class InvitationConflict(InvitationError):
    """A concurrency conflict occurred while processing the invitation."""
