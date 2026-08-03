"""APP_PUBLIC_URL: the one address a client is told to open.

The backend cannot infer its own public domain, so the operator declares it.
These tests pin the two things that matter downstream: the value is normalised
before anyone reads it, and every caller that hands a URL to a client reads it
from here rather than inventing a localhost address.
"""

import pytest

from app.application.onboarding.handover import build_handover_message
from app.core import public_url as public_url_module
from app.core.public_url import (
    PUBLIC_URL_PLACEHOLDER,
    is_public_url_configured,
    public_login_url,
)
from test_config import build_settings


@pytest.fixture
def configured_url(monkeypatch):
    """Point the module at a settings object carrying a real public URL."""

    def _configure(raw: str):
        monkeypatch.setattr(
            public_url_module, "settings", build_settings(APP_PUBLIC_URL=raw)
        )

    return _configure


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("https://accounting.example.com", "https://accounting.example.com"),
        # A trailing slash would double up against the paths appended downstream.
        ("https://accounting.example.com/", "https://accounting.example.com"),
        ("  https://app.city-technology.com  ", "https://app.city-technology.com"),
        ("http://localhost:5173", "http://localhost:5173"),
    ],
)
def test_the_configured_url_is_normalised(configured_url, raw, expected):
    configured_url(raw)

    assert public_login_url() == expected
    assert is_public_url_configured() is True


@pytest.mark.parametrize("raw", ["", "   ", "/"])
def test_an_unconfigured_url_falls_back_to_the_placeholder(configured_url, raw):
    configured_url(raw)

    assert public_login_url() == PUBLIC_URL_PLACEHOLDER
    assert is_public_url_configured() is False


def test_the_handover_message_carries_the_configured_url(configured_url):
    configured_url("https://accounting.example.com/")

    message = build_handover_message(
        company_name="Northwind Trading",
        admin_email="admin@northwind.test",
        temporary_password="Sw1ftPelican42",
        expires_at=None,
        login_url=public_login_url(),
    )

    assert "Login URL: https://accounting.example.com" in message
    assert PUBLIC_URL_PLACEHOLDER not in message


def test_the_handover_message_names_the_missing_url_instead_of_guessing(
    configured_url,
):
    configured_url("")

    message = build_handover_message(
        company_name="Northwind Trading",
        admin_email="admin@northwind.test",
        temporary_password="Sw1ftPelican42",
        expires_at=None,
        login_url=public_login_url(),
    )

    assert f"Login URL: {PUBLIC_URL_PLACEHOLDER}" in message
    assert "localhost" not in message
