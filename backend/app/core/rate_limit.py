"""Rate-limit counters, shared by every worker process.

These used to live in a module-level dict.  uvicorn runs with ``--workers 2``
(backend/Dockerfile), so there were two dicts and the operator's configured
limit was really twice what they set: measured, 40 failed logins against a
limit of 5 were answered with 10 x 401 rather than 5, and a 429 did not end the
attempt -- the next request landed on the other worker and was answered 401
again.  The counters now live in ``rate_limit_attempts``.

THE ORDERING TRAP, and why every function here opens its own session.

The login endpoint records a failed attempt and then raises 401.  ``get_db``
(database.py:25-30) yields the request session and only closes it -- there is no
rollback and no commit -- and closing a session with an open transaction
discards it.  A failed login's audit row survives today only because
``create_audit_log`` is called with ``commit=True`` immediately after
``record_attempt``, which sweeps both into one commit.

If the limiter wrote through the request session, its durability would be a
property of that call ordering.  Move the audit call, drop its commit, or add
an early return, and the recorded attempt vanishes -- and a vanished attempt is
a free retry, which is the entire control.  So the limiter does not touch the
request session at all.  Each function below opens a short-lived session of its
own and commits it before returning; nothing the request transaction does
afterwards, including being discarded, can undo it.

``test_rate_limiter_owns_its_transaction.py`` fails if someone reintroduces the
coupling by passing a session in.
"""

import threading
import time
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy import delete, func, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.accounting.models.rate_limit_attempt import RateLimitAttempt


# Retained only so that callers importing these names keep working; the counters
# are the table now, and clearing this dict does not reset a limiter.  It never
# reset the server's either -- the test suite talks to a separate process.
_attempts: dict[str, list[float]] = {}
_lock = threading.Lock()


# How often any one process runs the global sweep, and how far back it deletes.
# The retention floor is derived from the configured windows rather than
# hardcoded, so raising a window cannot start deleting rows the limiter is still
# counting.
_SWEEP_INTERVAL_SECONDS = 300
_sweep_lock = threading.Lock()
_last_sweep_at = 0.0


def get_client_ip(request: Request) -> str:
    if request.client:
        return request.client.host

    return "unknown"


def make_rate_limit_key(
    prefix: str,
    request: Request,
    identifier: str | None = None,
) -> str:
    ip = get_client_ip(request)

    if identifier:
        return f"{prefix}:{ip}:{identifier}"

    return f"{prefix}:{ip}"


def _cutoff(window_seconds: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=window_seconds)


def _retention_seconds() -> int:
    """The longest window any caller uses, so the sweep never deletes a row that
    is still inside somebody's window."""
    return max(
        settings.AUTH_FAILED_LOGIN_WINDOW_SECONDS,
        settings.AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
    )


def _sweep_if_due() -> None:
    """Delete attempts older than any window in use.

    Buckets that are written to prune themselves on every write, but a bucket
    that is never revisited -- a one-off address -- would otherwise keep its
    rows forever.  This runs at most once per _SWEEP_INTERVAL_SECONDS per
    process, on the write path, so it costs nothing on reads.
    """
    global _last_sweep_at

    now = time.monotonic()
    with _sweep_lock:
        if _last_sweep_at and now - _last_sweep_at < _SWEEP_INTERVAL_SECONDS:
            return
        _last_sweep_at = now

    with SessionLocal() as db:
        db.execute(
            delete(RateLimitAttempt).where(
                RateLimitAttempt.attempted_at <= _cutoff(_retention_seconds())
            )
        )
        db.commit()


def is_rate_limited(key: str, limit: int, window_seconds: int) -> bool:
    with SessionLocal() as db:
        current_count = db.scalar(
            select(func.count())
            .select_from(RateLimitAttempt)
            .where(
                RateLimitAttempt.bucket_key == key,
                RateLimitAttempt.attempted_at > _cutoff(window_seconds),
            )
        )

    return (current_count or 0) >= limit


def record_attempt(key: str, window_seconds: int) -> None:
    with SessionLocal() as db:
        # Prune this bucket first, so a long-lived key cannot accumulate rows
        # that are outside every window but still counted against the table.
        db.execute(
            delete(RateLimitAttempt).where(
                RateLimitAttempt.bucket_key == key,
                RateLimitAttempt.attempted_at <= _cutoff(window_seconds),
            )
        )
        db.add(
            RateLimitAttempt(
                bucket_key=key,
                attempted_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

    _sweep_if_due()


def reset_attempts(key: str) -> None:
    with SessionLocal() as db:
        db.execute(delete(RateLimitAttempt).where(RateLimitAttempt.bucket_key == key))
        db.commit()
