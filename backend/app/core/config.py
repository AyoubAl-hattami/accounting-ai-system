from typing import Literal
from urllib.parse import urlsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_SECRET_KEY = "change-this-secret-key-in-production"
MINIMUM_PRODUCTION_SECRET_KEY_LENGTH = 32
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
MAXIMUM_RECOMMENDED_PRODUCTION_TOKEN_MINUTES = 60


def _is_local_host(hostname: str | None) -> bool:
    return (hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}


def _validate_https_origin(value: str, *, field_name: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"Production {field_name} must be an HTTPS origin.")
    if _is_local_host(parsed.hostname):
        raise ValueError(f"Production {field_name} must not use localhost.")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError(f"Production {field_name} must be an origin without a path.")
    hostname = parsed.hostname.lower()
    if (
        hostname.endswith(".trycloudflare.com")
        or hostname.endswith(".example.com")
        or hostname.endswith(".example.invalid")
        or hostname in {"example.com", "example.invalid"}
    ):
        raise ValueError(f"Production {field_name} must not use a demo or placeholder host.")


class Settings(BaseSettings):
    APP_NAME: str = "Accounting AI System"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"

    # Where clients reach the frontend, e.g. https://accounting.example.com.
    # Left empty the handover message falls back to a visible placeholder rather
    # than to a localhost URL no client could ever open.
    APP_PUBLIC_URL: str = ""

    DATABASE_URL: str

    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES
    PRODUCTION_ALLOW_LONG_LIVED_TOKENS: bool = False
    ALGORITHM: Literal["HS256"] = "HS256"

    # None preserves convenient development registration while making the
    # production default closed. Production explicitly rejects True.
    PUBLIC_REGISTRATION_ENABLED: bool | None = None
    PRODUCTION_ALLOW_LOCAL_DATABASE: bool = False
    PRODUCTION_ALLOW_DATABASE_WITHOUT_TLS: bool = False
    PRODUCTION_SUBSCRIPTION_FAIL_CLOSED: bool = True
    VITE_PUBLIC_DEMO: bool = False

    AUTH_FAILED_LOGIN_LIMIT: int = 5
    AUTH_FAILED_LOGIN_WINDOW_SECONDS: int = 60

    AUTH_REGISTER_RATE_LIMIT: int = 20
    AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS: int = 60

    AI_JOURNAL_PROVIDER: str = "rules"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:3000,"
        "http://127.0.0.1:3000"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.APP_ENV.strip().lower() != "production":
            return self

        secret_key = self.SECRET_KEY.strip()
        if (
            secret_key == DEFAULT_SECRET_KEY
            or len(secret_key) < MINIMUM_PRODUCTION_SECRET_KEY_LENGTH
            or any(
                marker in secret_key.lower()
                for marker in ("not-for-production", "ci-static", "development-secret")
            )
        ):
            raise ValueError(
                "Production requires an explicitly configured SECRET_KEY "
                f"with at least {MINIMUM_PRODUCTION_SECRET_KEY_LENGTH} characters."
            )

        if "ACCESS_TOKEN_EXPIRE_MINUTES" not in self.model_fields_set:
            raise ValueError(
                "Production requires ACCESS_TOKEN_EXPIRE_MINUTES to be explicitly configured."
            )
        if self.ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive.")
        if (
            self.ACCESS_TOKEN_EXPIRE_MINUTES
            > MAXIMUM_RECOMMENDED_PRODUCTION_TOKEN_MINUTES
            and not self.PRODUCTION_ALLOW_LONG_LIVED_TOKENS
        ):
            raise ValueError(
                "Production access-token TTL exceeds 60 minutes; shorten it or set "
                "PRODUCTION_ALLOW_LONG_LIVED_TOKENS=true with documented risk acceptance."
            )

        public_url = self.APP_PUBLIC_URL.strip().rstrip("/")
        if not public_url:
            raise ValueError("Production requires APP_PUBLIC_URL.")
        _validate_https_origin(public_url, field_name="APP_PUBLIC_URL")

        database_url = self.DATABASE_URL.strip()
        parsed_database = urlsplit(database_url.replace("postgresql+psycopg2", "postgresql", 1))
        if parsed_database.scheme not in {"postgres", "postgresql"}:
            raise ValueError("Production DATABASE_URL must use PostgreSQL.")
        if _is_local_host(parsed_database.hostname) and not self.PRODUCTION_ALLOW_LOCAL_DATABASE:
            raise ValueError(
                "Production DATABASE_URL must not use localhost unless "
                "PRODUCTION_ALLOW_LOCAL_DATABASE=true is explicitly risk-accepted."
            )
        database_query = {
            key.lower(): value.lower()
            for key, value in (
                item.split("=", 1)
                for item in parsed_database.query.split("&")
                if "=" in item
            )
        }
        if (
            database_query.get("sslmode") not in {"require", "verify-ca", "verify-full"}
            and not self.PRODUCTION_ALLOW_DATABASE_WITHOUT_TLS
        ):
            raise ValueError(
                "Production DATABASE_URL must require TLS with sslmode=require, "
                "verify-ca, or verify-full unless explicitly risk-accepted."
            )

        origins = self.cors_origins_list
        if not origins:
            raise ValueError("Production requires at least one CORS_ORIGINS value.")
        for origin in origins:
            if "*" in origin:
                raise ValueError("Production CORS_ORIGINS must not contain wildcards.")
            _validate_https_origin(origin.rstrip("/"), field_name="CORS_ORIGINS")

        if self.PUBLIC_REGISTRATION_ENABLED is True:
            raise ValueError("Public registration must be disabled in production.")
        if not self.PRODUCTION_SUBSCRIPTION_FAIL_CLOSED:
            raise ValueError("Production subscription enforcement must fail closed.")
        if self.VITE_PUBLIC_DEMO:
            raise ValueError("VITE_PUBLIC_DEMO must not be enabled in production.")
        provider = self.AI_JOURNAL_PROVIDER.strip().lower()
        if provider not in {"rules", "openai", "gemini"}:
            raise ValueError(
                "Production AI_JOURNAL_PROVIDER must be rules, openai, or gemini; "
                f"received {provider}."
            )
        if provider == "openai" and not self.OPENAI_API_KEY.strip():
            raise ValueError("OPENAI_API_KEY is required for the OpenAI provider.")
        if provider == "gemini" and not self.GEMINI_API_KEY.strip():
            raise ValueError("GEMINI_API_KEY is required for the Gemini provider.")

        return self

    @property
    def app_public_url(self) -> str:
        """APP_PUBLIC_URL without its trailing slash; empty when unconfigured."""
        return self.APP_PUBLIC_URL.strip().rstrip("/")

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def public_registration_enabled(self) -> bool:
        if self.PUBLIC_REGISTRATION_ENABLED is not None:
            return self.PUBLIC_REGISTRATION_ENABLED
        return self.APP_ENV.strip().lower() not in {"production"}


settings = Settings()
