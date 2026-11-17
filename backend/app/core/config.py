from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "SmartInventory AI"
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://inventory:local-dev-only@127.0.0.1:5432/smartinventory"
    )
    db_connect_timeout: int = Field(default=3, ge=1, le=30)
    cors_origins: list[str] = ["http://localhost:5173"]
    jwt_secret: SecretStr | None = Field(default=None, min_length=32)
    access_token_minutes: int = Field(default=30, ge=1, le=120)
    ai_provider: Literal["disabled", "openai", "gemini", "mock"] = "disabled"
    ai_model: str = Field(default="", max_length=100)
    ai_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    ai_base_url: str | None = None
    ai_timeout_seconds: int = Field(default=12, ge=1, le=20)
    ai_requests_per_minute: int = Field(default=6, ge=1, le=30)

    @field_validator("ai_base_url")
    @classmethod
    def validate_ai_url(cls, value: str | None) -> str | None:
        from urllib.parse import urlsplit

        if not value or not value.strip():
            return None
        parsed = urlsplit(value)
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if (
            (parsed.scheme != "https" and not (parsed.scheme == "http" and local))
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("AI_BASE_URL must use HTTPS (HTTP allowed only on loopback)")
        return value.rstrip("/")

    @property
    def ai_endpoint(self) -> str:
        if self.ai_base_url:
            return self.ai_base_url
        if self.ai_provider == "gemini":
            return "https://generativelanguage.googleapis.com/v1beta"
        return "https://api.openai.com/v1"

    @field_validator("database_url")
    @classmethod
    def require_postgresql(cls, value: SecretStr) -> SecretStr:
        try:
            valid = make_url(value.get_secret_value()).drivername == "postgresql+psycopg"
        except Exception:
            valid = False
        if not valid:
            raise ValueError("DATABASE_URL must use postgresql+psycopg")
        return value
