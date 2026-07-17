from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_SECRET_KEY = "change-this-secret-key-in-production"
MINIMUM_PRODUCTION_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    APP_NAME: str = "Accounting AI System"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"

    DATABASE_URL: str

    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: Literal["HS256"] = "HS256"

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
    def validate_production_secret_key(self) -> "Settings":
        if self.APP_ENV.strip().lower() != "production":
            return self

        secret_key = self.SECRET_KEY.strip()
        if (
            secret_key == DEFAULT_SECRET_KEY
            or len(secret_key) < MINIMUM_PRODUCTION_SECRET_KEY_LENGTH
        ):
            raise ValueError(
                "Production requires an explicitly configured SECRET_KEY "
                f"with at least {MINIMUM_PRODUCTION_SECRET_KEY_LENGTH} characters."
            )

        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()