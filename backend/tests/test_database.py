import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.mark.integration
def test_readiness_against_real_postgresql():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL database")
    settings = Settings(_env_file=None, database_url=url)
    with TestClient(create_app(settings)) as client:
        response = client.get("/health/ready")
        assert response.status_code == 200, response.text


def test_real_connection_failure_returns_sanitized_503():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://offline:secret@127.0.0.1:1/offline",
        db_connect_timeout=1,
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert "secret" not in response.text
