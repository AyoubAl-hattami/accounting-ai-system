"""Temporary-password generation for client handover.

Kept in the application layer because it is pure: ``secrets`` is stdlib and no
framework, session, or model is involved.  The generated value is returned to
the caller exactly once and is never persisted in clear text.
"""

from __future__ import annotations

import secrets

# Ambiguous glyphs are excluded (0/O, 1/l/I) because this password is read off a
# screen, pasted into a chat message, and typed by hand by the client.
_LOWER = "abcdefghijkmnopqrstuvwxyz"
_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"
_DIGITS = "23456789"
_ALPHABET = _LOWER + _UPPER + _DIGITS

# Comfortably above the 8-character policy minimum: this credential travels
# through a chat message before the client changes it.
TEMPORARY_PASSWORD_LENGTH = 16


def generate_temporary_password(length: int = TEMPORARY_PASSWORD_LENGTH) -> str:
    """Return a random password guaranteed to satisfy the password policy.

    One character of each required class is placed first and the remainder is
    filled at random, then the whole string is shuffled — so the guarantee never
    shows up as a predictable prefix.
    """
    if length < 8:
        raise ValueError("Temporary passwords must be at least 8 characters")

    rng = secrets.SystemRandom()
    characters = [
        rng.choice(_LOWER),
        rng.choice(_UPPER),
        rng.choice(_DIGITS),
    ]
    characters.extend(rng.choice(_ALPHABET) for _ in range(length - len(characters)))
    rng.shuffle(characters)
    return "".join(characters)
