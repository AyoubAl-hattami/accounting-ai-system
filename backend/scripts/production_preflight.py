"""Validate staging or production configuration without printing secret values."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import parse_qs, urlsplit


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
APPROVED_AI_PROVIDERS = {"rules", "openai", "gemini"}
FALSE_VALUES = {"", "0", "false", "no", "off"}
UNSAFE_SECRET_MARKERS = (
    "change-this-secret",
    "not-for-production",
    "ci-static",
    "development-secret",
)
FORBIDDEN_HOSTS = {"localhost", "127.0.0.1", "::1", "example.com", "example.invalid"}
REQUIRED_SCRIPT_GUARDS = {
    "backend/scripts/seed_demo_data.py": ("production", "Refusing to run"),
    "backend/scripts/cleanup_local_demo_data.py": ("APP_ENV=development",),
    "backend/scripts/reset_company_data.py": ("APP_ENV=development",),
    "backend/restore_admin.py": ("production", "forbidden"),
    "scripts/start-public-demo.ps1": ("APP_ENV=production", "forbidden"),
}


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    passed: bool
    message: str


def _value(env: Mapping[str, str], name: str) -> str:
    return env.get(name, "").strip()


def _is_forbidden_hostname(hostname: str | None) -> bool:
    host = (hostname or "").lower()
    return (
        not host
        or host in FORBIDDEN_HOSTS
        or host.endswith(".example.com")
        or host.endswith(".example.invalid")
        or host.endswith(".trycloudflare.com")
    )


def _exact_https_origin(value: str) -> bool:
    parsed = urlsplit(value)
    return (
        parsed.scheme == "https"
        and not _is_forbidden_hostname(parsed.hostname)
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
        and "*" not in value
    )


def _check(name: str, passed: bool, success: str, failure: str) -> CheckResult:
    return CheckResult(name=name, passed=passed, message=success if passed else failure)


def validate_environment(
    env: Mapping[str, str],
    *,
    mode: str,
    repository_root: Path = REPOSITORY_ROOT,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    app_env = _value(env, "APP_ENV").lower()
    results.append(
        _check(
            "APP_ENV",
            app_env == mode,
            f"matches requested {mode} mode",
            f"must be exactly {mode}",
        )
    )

    public_url = _value(env, "APP_PUBLIC_URL").rstrip("/")
    results.append(
        _check(
            "APP_PUBLIC_URL",
            _exact_https_origin(public_url),
            "is an exact non-placeholder HTTPS origin",
            "must be an exact HTTPS origin without localhost, tunnel, or placeholder host",
        )
    )

    database_url = _value(env, "DATABASE_URL")
    normalized_database_url = database_url.replace("postgresql+psycopg2", "postgresql", 1)
    parsed_database = urlsplit(normalized_database_url)
    postgres = parsed_database.scheme in {"postgres", "postgresql"}
    results.append(
        _check(
            "DATABASE_URL_DRIVER",
            postgres,
            "uses PostgreSQL",
            "must use PostgreSQL and must not use SQLite",
        )
    )
    nonlocal_database = not _is_forbidden_hostname(parsed_database.hostname)
    results.append(
        _check(
            "DATABASE_URL_HOST",
            postgres and nonlocal_database,
            "uses a non-local, non-placeholder database host",
            "must not use localhost, loopback, or a placeholder host",
        )
    )
    sslmode = parse_qs(parsed_database.query).get("sslmode", [""])[0].lower()
    results.append(
        _check(
            "DATABASE_URL_TLS",
            sslmode in {"require", "verify-ca", "verify-full"},
            "requires PostgreSQL TLS",
            "must set sslmode=require, verify-ca, or verify-full",
        )
    )

    secret = _value(env, "SECRET_KEY")
    strong_secret = len(secret) >= 32 and not any(
        marker in secret.lower() for marker in UNSAFE_SECRET_MARKERS
    )
    results.append(
        _check(
            "SECRET_KEY",
            strong_secret,
            "is present and passes strength screening",
            "must be at least 32 characters and not a known development/CI value",
        )
    )

    ttl_raw = _value(env, "ACCESS_TOKEN_EXPIRE_MINUTES")
    try:
        ttl = int(ttl_raw)
    except ValueError:
        ttl = 0
    results.append(
        _check(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            bool(ttl_raw) and 1 <= ttl <= 60,
            "is explicitly set between 1 and 60 minutes",
            "must be explicitly set to an integer between 1 and 60",
        )
    )

    cors_values = [
        value.strip().rstrip("/")
        for value in _value(env, "CORS_ORIGINS").split(",")
        if value.strip()
    ]
    results.append(
        _check(
            "CORS_ORIGINS",
            bool(cors_values) and all(_exact_https_origin(origin) for origin in cors_values),
            "contains only exact non-placeholder HTTPS origins",
            "must contain exact HTTPS origins only; no wildcard, path, localhost, or placeholder",
        )
    )

    provider = _value(env, "AI_JOURNAL_PROVIDER").lower()
    provider_ready = provider in APPROVED_AI_PROVIDERS
    if provider == "openai":
        provider_ready = bool(_value(env, "OPENAI_API_KEY"))
    elif provider == "gemini":
        provider_ready = bool(_value(env, "GEMINI_API_KEY"))
    results.append(
        _check(
            "AI_JOURNAL_PROVIDER",
            provider_ready,
            "uses an approved provider with required configuration",
            "must be rules, openai with a key, or gemini with a key",
        )
    )

    demo_value = _value(env, "VITE_PUBLIC_DEMO").lower()
    results.append(
        _check(
            "VITE_PUBLIC_DEMO",
            demo_value in FALSE_VALUES,
            "is disabled",
            "must be unset or a false value",
        )
    )

    api_base = _value(env, "VITE_API_BASE_URL").rstrip("/")
    api_base_safe = api_base == "/api" or _exact_https_origin(api_base)
    results.append(
        _check(
            "VITE_API_BASE_URL",
            api_base_safe,
            "uses same-origin /api or an exact HTTPS origin",
            "must be /api or an exact non-placeholder HTTPS origin",
        )
    )

    for relative_path, markers in REQUIRED_SCRIPT_GUARDS.items():
        path = repository_root / relative_path
        try:
            content = path.read_text(encoding="utf-8-sig")
        except OSError:
            guarded = False
        else:
            guarded = all(marker in content for marker in markers)
        results.append(
            _check(
                f"SCRIPT_GUARD:{relative_path}",
                guarded,
                "production refusal marker present",
                "missing required production refusal marker",
            )
        )

    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("staging", "production"), required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    results = validate_environment(os.environ, mode=args.mode)
    print(f"Deployment preflight: mode={args.mode}; checks={len(results)}")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.message}")
    failed = sum(not result.passed for result in results)
    print(f"Preflight result: {'PASS' if failed == 0 else 'FAIL'}; failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
