"""The public address clients are told to log in at.

The backend cannot infer the domain it is served behind — a request Host header
is attacker-controlled and a reverse proxy may rewrite it — so the operator
declares it once through ``APP_PUBLIC_URL``.  Until they do, every caller shows
the same obvious placeholder rather than a localhost URL no client could open.
"""

from app.core.config import settings

PUBLIC_URL_PLACEHOLDER = "[add your domain here]"


def public_login_url() -> str:
    """Return the configured public app URL, or the placeholder if unset."""
    return settings.app_public_url or PUBLIC_URL_PLACEHOLDER


def is_public_url_configured() -> bool:
    return bool(settings.app_public_url)
