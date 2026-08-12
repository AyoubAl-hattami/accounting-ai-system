import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_SECRET_KEY, Settings


TEST_DATABASE_URL = "postgresql+psycopg2://test:test@localhost/test"
VALID_PRODUCTION_SECRET = "a9F2!vQ7#kL4@xP8$zR6&mN3*wT5^cD1"
VALID_PRODUCTION_VALUES = {
    "APP_PUBLIC_URL": "https://ledger.acme.test",
    "DATABASE_URL": "postgresql+psycopg2://app:secret@db.internal/ledger?sslmode=verify-full",
    "SECRET_KEY": VALID_PRODUCTION_SECRET,
    "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
    "CORS_ORIGINS": "https://ledger.acme.test",
}


def build_settings(**overrides) -> Settings:
    values: dict = {
        "DATABASE_URL": TEST_DATABASE_URL,
        "_env_file": None,
    }
    if str(overrides.get("APP_ENV", "")).lower() == "production":
        values.update(VALID_PRODUCTION_VALUES)
    values.update(overrides)
    return Settings(**values)


def test_production_rejects_default_secret_key():
    with pytest.raises(ValidationError, match="Production requires"):
        build_settings(APP_ENV="production", SECRET_KEY=DEFAULT_SECRET_KEY)


@pytest.mark.parametrize("secret_key", ["", "short-secret"])
def test_production_rejects_empty_or_weak_secret_key(secret_key):
    with pytest.raises(ValidationError, match="Production requires"):
        build_settings(APP_ENV="production", SECRET_KEY=secret_key)


def test_production_accepts_valid_high_entropy_secret_key():
    settings = build_settings(APP_ENV="production", SECRET_KEY=VALID_PRODUCTION_SECRET)

    assert settings.SECRET_KEY == VALID_PRODUCTION_SECRET
    assert settings.ALGORITHM == "HS256"
    assert settings.public_registration_enabled is False


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_non_production_environments_preserve_local_secret_compatibility(app_env):
    settings = build_settings(APP_ENV=app_env, SECRET_KEY=DEFAULT_SECRET_KEY)

    assert settings.SECRET_KEY == DEFAULT_SECRET_KEY


def test_production_requires_explicit_access_token_ttl():
    values = dict(VALID_PRODUCTION_VALUES)
    values.pop("ACCESS_TOKEN_EXPIRE_MINUTES")
    with pytest.raises(ValidationError, match="explicitly configured"):
        Settings(APP_ENV="production", _env_file=None, **values)


def test_production_rejects_long_lived_token_without_risk_acceptance():
    with pytest.raises(ValidationError, match="exceeds 60 minutes"):
        build_settings(APP_ENV="production", ACCESS_TOKEN_EXPIRE_MINUTES=1440)


def test_production_allows_documented_long_lived_token_override():
    configured = build_settings(
        APP_ENV="production",
        ACCESS_TOKEN_EXPIRE_MINUTES=120,
        PRODUCTION_ALLOW_LONG_LIVED_TOKENS=True,
    )
    assert configured.ACCESS_TOKEN_EXPIRE_MINUTES == 120


@pytest.mark.parametrize(
    "field_name, value, message",
    [
        ("APP_PUBLIC_URL", "http://ledger.acme.test", "HTTPS origin"),
        ("APP_PUBLIC_URL", "https://localhost", "localhost"),
        ("APP_PUBLIC_URL", "https://tenant.trycloudflare.com", "demo or placeholder"),
        ("DATABASE_URL", "sqlite:///production.db", "PostgreSQL"),
        ("DATABASE_URL", TEST_DATABASE_URL, "must not use localhost"),
        (
            "DATABASE_URL",
            "postgresql+psycopg2://app:secret@db.internal/ledger",
            "must require TLS",
        ),
        ("CORS_ORIGINS", "*", "wildcards"),
        ("CORS_ORIGINS", "http://ledger.acme.test", "HTTPS origin"),
        ("CORS_ORIGINS", "https://ledger.acme.test/api", "without a path"),
    ],
)
def test_production_rejects_unsafe_network_configuration(field_name, value, message):
    with pytest.raises(ValidationError, match=message):
        build_settings(APP_ENV="production", **{field_name: value})


def test_production_rejects_public_registration_demo_mode_and_placeholder_ai():
    for override, message in [
        ({"PUBLIC_REGISTRATION_ENABLED": True}, "registration"),
        ({"VITE_PUBLIC_DEMO": True}, "VITE_PUBLIC_DEMO"),
        ({"AI_JOURNAL_PROVIDER": "llm_placeholder"}, "llm_placeholder"),
    ]:
        with pytest.raises(ValidationError, match=message):
            build_settings(APP_ENV="production", **override)


def test_development_registration_remains_enabled_by_default():
    assert build_settings(APP_ENV="development").public_registration_enabled is True
