"""Domain exceptions for user credential changes.

Framework-neutral: the auth route catches these and maps each to an HTTP
status.  Nothing here knows what a status code is.
"""

from __future__ import annotations


class UserError(Exception):
    """Base for all user credential errors."""


class UserNotFound(UserError):
    """No account exists for the given id."""


class CurrentPasswordMismatch(UserError):
    """The supplied current password does not match the stored hash."""


class NewPasswordReused(UserError):
    """The new password is identical to the one being replaced.

    A temporary credential that travelled over chat or email is compromised the
    moment it is sent, so re-entering it would defeat the whole handover.
    """
