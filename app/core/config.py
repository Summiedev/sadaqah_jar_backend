from pathlib import Path
from typing import Any, Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Absolute path so settings load regardless of the current working
        # directory (uvicorn, celery, alembic, or pytest launched from the repo
        # root all resolve the same file instead of silently finding nothing).
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str
    ENV: str

    DATABASE_URL: str
    REDIS_URL: str

    JWT_SECRET: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int
    CORS_ORIGINS: Annotated[list[str], NoDecode] = []

    # SMTP / email settings (used for verification & password-reset emails)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@mizan.app"

    # Public-facing base URL for email links (no trailing slash)
    APP_URL: str = "http://localhost:8000"

    GOOGLE_CLIENT_ID: str = ""

    RESEND_API_KEY: str = ""

    # Aladhan calculation method ID; 2 is ISNA. Override for the convention
    # used by your audience without changing application code.
    PRAYER_CALCULATION_METHOD: int = 2
    PRAYER_API_TIMEOUT_SECONDS: float = 10.0

    # Absolute path to a Firebase service-account JSON file. Keep this secret
    # out of source control; leaving it blank makes push delivery a no-op.
    FCM_SERVICE_ACCOUNT_PATH: str = ""

    # Quran Foundation Content API. These are intentionally optional so local
    # development can run before the dataset import is configured.
    QF_CLIENT_ID: str = ""
    QF_CLIENT_SECRET: str = ""
    QF_ENV: str = "production"

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        secret = value.strip()
        if len(secret) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long")
        return secret

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_access_token_expiry(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero")
        return value

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        if isinstance(value, list):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        raise ValueError("CORS_ORIGINS must be a comma-separated string or a list")


settings = Settings()

API_V1_PREFIX = "/api/v1"
