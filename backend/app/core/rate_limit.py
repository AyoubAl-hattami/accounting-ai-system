import time
import threading

from fastapi import Request


# In-memory storage: key -> list of timestamps (monotonic)
_attempts: dict[str, list[float]] = {}
_lock = threading.Lock()


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


def _clean_old_entries(key: str, window_seconds: int) -> None:
    cutoff = time.monotonic() - window_seconds

    if key in _attempts:
        _attempts[key] = [
            ts for ts in _attempts[key]
            if ts > cutoff
        ]

        if not _attempts[key]:
            del _attempts[key]


def is_rate_limited(key: str, limit: int, window_seconds: int) -> bool:
    with _lock:
        _clean_old_entries(key, window_seconds)

        current_count = len(_attempts.get(key, []))

        return current_count >= limit


def record_attempt(key: str, window_seconds: int) -> None:
    with _lock:
        _clean_old_entries(key, window_seconds)

        if key not in _attempts:
            _attempts[key] = []

        _attempts[key].append(time.monotonic())


def reset_attempts(key: str) -> None:
    with _lock:
        _attempts.pop(key, None)
