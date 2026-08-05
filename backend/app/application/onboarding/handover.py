"""The message a platform owner sends a newly onboarded client.

Pure string assembly, so both the HTTP route and the CLI helper produce exactly
the same text.  The frontend renders its own localized copy from the structured
response; this is the English source of truth and the only version the CLI has.
"""

from __future__ import annotations

from datetime import datetime

NO_EXPIRY_TEXT = "No expiry date"


def format_expiry(expires_at: datetime | None) -> str:
    return expires_at.strftime("%Y-%m-%d") if expires_at is not None else NO_EXPIRY_TEXT


def build_handover_message(
    *,
    company_name: str,
    admin_email: str,
    temporary_password: str | None,
    expires_at: datetime | None,
    login_url: str,
) -> str:
    """Return the ready-to-copy handover text.

    ``temporary_password`` is None when an existing account was reused — there is
    no new credential to hand over, and inventing one would silently reset a
    password the client is already using.
    """
    lines = [
        "Hello,",
        "",
        "Your accounting system access has been created.",
        "",
        f"Login URL: {login_url}",
        f"Company: {company_name}",
        f"Admin email: {admin_email}",
    ]

    if temporary_password:
        lines.append(f"Temporary password: {temporary_password}")

    lines.extend(
        [
            f"Subscription valid until: {format_expiry(expires_at)}",
            "",
        ]
    )

    if temporary_password:
        lines.append(
            "This password is temporary. The system will ask you to set a new "
            "one the first time you log in, and nothing else opens until you "
            "do. You can then invite your team members from Company Users."
        )
    else:
        lines.append(
            "Please log in with your existing password. You can then invite your "
            "team members from Company Users."
        )

    return "\n".join(lines)
