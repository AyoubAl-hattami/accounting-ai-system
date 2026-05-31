from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Accounting AI System"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"

    DATABASE_URL: str

    SECRET_KEY: str = "change-this-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"

    AUTH_FAILED_LOGIN_LIMIT: int = 5
    AUTH_FAILED_LOGIN_WINDOW_SECONDS: int = 60

    AUTH_REGISTER_RATE_LIMIT: int = 20
    AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS: int = 60

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

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()