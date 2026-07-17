import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_SECRET_KEY, Settings


TEST_DATABASE_URL = "postgresql+psycopg2://test:test@localhost/test"
VALID_PRODUCTION_SECRET = "a9F2!vQ7#kL4@xP8$zR6&mN3*wT5^cD1"


def build_settings(**overrides) -> Settings:
    values = {
        "DATABASE_URL": TEST_DATABASE_URL,
        "_env_file": None,
        **overrides,
    }
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


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_non_production_environments_preserve_local_secret_compatibility(app_env):
    settings = build_settings(APP_ENV=app_env, SECRET_KEY=DEFAULT_SECRET_KEY)

    assert settings.SECRET_KEY == DEFAULT_SECRET_KEY