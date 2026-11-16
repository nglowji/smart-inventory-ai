import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_environment_overrides_defaults(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Test inventory")
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')
    config = Settings(_env_file=None)
    assert config.app_name == "Test inventory"
    assert config.cors_origins == ["http://localhost:3000"]
    assert "local-dev-only" not in repr(config)


def test_rejects_non_postgresql_database():
    with pytest.raises(ValidationError, match="postgresql"):
        Settings(_env_file=None, database_url="sqlite://")
