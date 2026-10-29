from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# hide_input_in_errors: a rejected secret must never be echoed into logs or tracebacks.
_SETTINGS_CONFIG = SettingsConfigDict(
    env_file=".env", env_prefix="VMP_", extra="ignore", hide_input_in_errors=True
)

# Fragments of documentation placeholders; a secret containing them was copied, not generated.
_PLACEHOLDER_SECRET_MARKERS = ("change-me", "changeme", "replace-with", "replace-me", "your-secret")
_MIN_DISTINCT_SECRET_CHARS = 10


class DatabaseSettings(BaseSettings):
    """Settings needed by tooling (migrations, seeding) that must not require secrets."""

    model_config = _SETTINGS_CONFIG

    database_url: str = "sqlite:///./data/vmp.db"


class Settings(DatabaseSettings):
    model_config = _SETTINGS_CONFIG

    app_name: str = "Visitor Management Platform"
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=60, gt=0, le=24 * 60)

    site_timezone: str = "UTC"

    login_rate_limit_attempts: int = Field(default=5, gt=0)
    # Per-account cap across all client addresses: stops guessing from rotating IPs.
    login_rate_limit_account_attempts: int = Field(default=20, gt=0)
    login_rate_limit_window_seconds: int = Field(default=60, gt=0)

    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("jwt_secret_key")
    @classmethod
    def _reject_weak_secret(cls, value: str) -> str:
        lowered = value.lower()
        if any(marker in lowered for marker in _PLACEHOLDER_SECRET_MARKERS):
            raise ValueError("is a placeholder; generate a random secret")
        if len(set(value)) < _MIN_DISTINCT_SECRET_CHARS:
            raise ValueError("is too predictable; generate a random secret")
        return value

    @field_validator("site_timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unknown timezone: {value}") from exc
        return value

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.site_timezone)

    @property
    def docs_enabled(self) -> bool:
        return self.environment != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
