"""Domain exceptions for the client-onboarding bounded context.

These are framework-neutral.  The platform onboarding route catches them and
maps each to an HTTP status; nothing here knows what a status code is.
"""

from __future__ import annotations


class OnboardingError(Exception):
    """Base for all client-onboarding domain errors."""


class CompanyNameTaken(OnboardingError):
    """A company with this name already exists.

    Company names are not unique at the database level (historic data contains
    duplicates), so this is a deliberate onboarding-time rule: the platform
    owner should never be able to create two tenants that look identical in the
    admin list by accident.
    """


class AdminEmailTaken(OnboardingError):
    """An account already exists for this email and reuse was not requested."""


class ReusedAdminIsPlatformAdmin(OnboardingError):
    """Refuses to attach the platform owner to a client company.

    Reusing an existing account is allowed, but never for a superuser: the
    platform owner is deliberately not a member of the companies it
    administers.
    """


class ReusedAdminIsInactive(OnboardingError):
    """The existing account is deactivated and must be restored explicitly."""


class MissingTemporaryPassword(OnboardingError):
    """A new admin account needs either a supplied or a generated password."""


class InvalidSubscriptionWindow(OnboardingError):
    """The requested subscription would be expired the moment it is created."""
