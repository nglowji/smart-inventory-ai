from pathlib import Path

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
