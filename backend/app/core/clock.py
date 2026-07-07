"""
Backend-derived "today" — single source of truth.

All Gemini Assistant journal entries must use this function for the entry date.
Centralised here so tests can mock it when needed (e.g. freezegun or monkeypatch).

Usage:
    from app.core.clock import get_today_date
    today = get_today_date()
"""

from datetime import date, datetime, timezone


def get_today_date() -> date:
    """Return today's date in UTC. Never hardcoded; always runtime-derived."""
    return datetime.now(timezone.utc).date()
