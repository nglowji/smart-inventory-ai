import json
import logging
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.logging import JsonFormatter
from app.main import create_app


def test_request_id_matches_header_and_error_body():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        correlation = str(uuid4())
        response = client.get("/api/v1/products", headers={"X-Request-ID": correlation})
        assert response.status_code == 401
        assert response.headers["X-Request-ID"] == correlation
        assert response.json()["error"]["request_id"] == correlation
        invalid = client.get("/health", headers={"X-Request-ID": "do-not-log-this-value"})
        assert UUID(invalid.headers["X-Request-ID"])


def test_http_logs_exclude_headers_query_and_passwords(caplog):
    with TestClient(create_app(Settings(_env_file=None))) as client:
        caplog.set_level(logging.INFO, logger="smartinventory.http")
        response = client.post(
            "/api/v1/auth/login?secret=private-query",
            headers={"Authorization": "Bearer private-token"},
            json={"email": "admin@example.com", "password": "private-password"},
        )
        assert response.status_code == 503
    records = [record for record in caplog.records if record.name == "smartinventory.http"]
    assert records
    rendered = "\n".join(JsonFormatter().format(record) for record in records)
    assert not any(
        secret in rendered
        for secret in ["private-query", "private-token", "private-password", "admin@example.com"]
    )
    log = json.loads(JsonFormatter().format(records[-1]))
    assert log["request_id"] == response.headers["X-Request-ID"]
    assert log["status"] == 503
    assert log["route"] == "/api/v1/auth/login"


def test_unhandled_errors_are_sanitized_without_exception_payload(caplog):
    app = create_app(Settings(_env_file=None))

    @app.get("/test-failure")
    def failure():
        raise RuntimeError("private-database-connection-string")

    with TestClient(app) as client:
        caplog.set_level(logging.INFO, logger="smartinventory.http")
        response = client.get("/test-failure")
    assert response.status_code == 500
    assert "private-database" not in response.text
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert "private-database" not in "\n".join(
        JsonFormatter().format(record) for record in caplog.records
    )
