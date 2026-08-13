from pathlib import Path

from scripts.production_preflight import main, validate_environment


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VALID_ENV = {
    "APP_ENV": "staging",
    "APP_PUBLIC_URL": "https://staging.ledger.acme.test",
    "DATABASE_URL": (
        "postgresql+psycopg2://app:do-not-print@db.internal/ledger"
        "?sslmode=verify-full"
    ),
    "SECRET_KEY": "A9-valid-but-test-only-secret-value-72xQ",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "CORS_ORIGINS": "https://staging.ledger.acme.test",
    "AI_JOURNAL_PROVIDER": "rules",
    "VITE_PUBLIC_DEMO": "0",
    "VITE_API_BASE_URL": "/api",
}


def failures(env: dict[str, str], mode: str = "staging") -> set[str]:
    return {
        result.name
        for result in validate_environment(env, mode=mode, repository_root=REPOSITORY_ROOT)
        if not result.passed
    }


def test_valid_staging_configuration_and_repository_guards_pass():
    assert failures(VALID_ENV) == set()


def test_valid_production_configuration_passes():
    env = {
        **VALID_ENV,
        "APP_ENV": "production",
        "APP_PUBLIC_URL": "https://ledger.acme.test",
        "CORS_ORIGINS": "https://ledger.acme.test",
    }
    assert failures(env, mode="production") == set()


def test_mode_must_match_app_environment():
    assert "APP_ENV" in failures(VALID_ENV, mode="production")


def test_preflight_rejects_unsafe_urls_database_secret_ttl_cors_and_demo():
    unsafe = {
        **VALID_ENV,
        "APP_PUBLIC_URL": "https://sample.trycloudflare.com",
        "DATABASE_URL": "sqlite:///local.db",
        "SECRET_KEY": "short",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "1440",
        "CORS_ORIGINS": "*",
        "VITE_PUBLIC_DEMO": "1",
        "VITE_API_BASE_URL": "http://127.0.0.1:8010",
    }
    assert {
        "APP_PUBLIC_URL",
        "DATABASE_URL_DRIVER",
        "DATABASE_URL_HOST",
        "DATABASE_URL_TLS",
        "SECRET_KEY",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "CORS_ORIGINS",
        "VITE_PUBLIC_DEMO",
        "VITE_API_BASE_URL",
    } <= failures(unsafe)


def test_external_ai_provider_requires_its_key():
    assert "AI_JOURNAL_PROVIDER" in failures(
        {**VALID_ENV, "AI_JOURNAL_PROVIDER": "openai"}
    )
    assert "AI_JOURNAL_PROVIDER" not in failures(
        {**VALID_ENV, "AI_JOURNAL_PROVIDER": "openai", "OPENAI_API_KEY": "redacted"}
    )


def test_cli_output_does_not_print_secrets_or_database_url(monkeypatch, capsys):
    for name, value in VALID_ENV.items():
        monkeypatch.setenv(name, value)

    assert main(["--mode", "staging"]) == 0
    output = capsys.readouterr().out
    assert "do-not-print" not in output
    assert VALID_ENV["SECRET_KEY"] not in output
    assert "Preflight result: PASS" in output


def test_missing_script_guard_fails_without_executing_the_script():
    missing_root = REPOSITORY_ROOT / "missing-production-artifacts"
    results = validate_environment(
        VALID_ENV,
        mode="staging",
        repository_root=missing_root,
    )
    assert any(
        result.name.startswith("SCRIPT_GUARD:") and not result.passed
        for result in results
    )
