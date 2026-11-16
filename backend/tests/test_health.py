from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_liveness_and_readiness_are_independent():
    settings = Settings(_env_file=None)
    with TestClient(create_app(settings)) as client:
        with patch("app.main.database_is_ready", return_value=False):
            assert client.get("/health").json() == {"status": "ok"}
            response = client.get("/health/ready")
        assert response.status_code == 503
        error = response.json()["error"]
        assert error["code"] == "DATABASE_UNAVAILABLE"
        assert error["request_id"] == response.headers["X-Request-ID"]
        assert "local-dev-only" not in response.text


def test_readiness_when_database_is_available():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        with patch("app.main.database_is_ready", return_value=True):
            response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "database": "available"}


def test_openapi_exposes_only_foundation_endpoints():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert set(client.get("/openapi.json").json()["paths"]) == {
            "/health", "/health/ready"
        }
