from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import User
from app.main import create_app


def test_catalog_requires_auth_without_touching_database():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get("/api/v1/products").status_code == 401
        assert client.post("/api/v1/categories", json={"name": "Test"}).status_code == 401


def test_missing_signing_key_disables_login():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "anything",
            },
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "AUTH_NOT_CONFIGURED"


@pytest.mark.integration
@pytest.mark.parametrize("role", ["STAFF", "VIEWER"])
def test_reader_can_read_but_cannot_mutate(catalog_client, role):
    login = catalog_client.post(
        "/api/v1/auth/login",
        json={
            "email": f"{role.lower()}@example.com",
            "password": "test-password-123",
        },
    )
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert catalog_client.get("/api/v1/products", headers=headers).status_code == 200
    assert catalog_client.get("/api/v1/auth/me", headers=headers).json()["role"] == role
    assert (
        catalog_client.post(
            "/api/v1/categories", headers=headers, json={"name": "Forbidden"}
        ).status_code
        == 403
    )
    assert (
        catalog_client.post(
            "/api/v1/products", headers=headers, json={"sku": "A", "name": "B", "unit": "PCS"}
        ).status_code
        == 403
    )


@pytest.mark.integration
def test_login_errors_do_not_disclose_user_or_password(catalog_client):
    bodies = []
    for email in ("admin@example.com", "absent@example.com"):
        response = catalog_client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "wrong-password",
            },
        )
        assert response.status_code == 401
        assert "wrong-password" not in response.text
        bodies.append(response.json()["error"]["message"])
    assert bodies[0] == bodies[1]


@pytest.mark.integration
def test_expired_and_invalid_token(catalog_client):
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": "not-a-real-user",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        catalog_client.app.state.settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    for token in ("invalid", expired):
        assert (
            catalog_client.get(
                "/api/v1/products",
                headers={
                    "Authorization": "Bearer " + token,
                },
            ).status_code
            == 401
        )


@pytest.mark.integration
def test_disabled_user_loses_access(catalog_client, admin_headers, catalog_db):
    with Session(catalog_db) as session, session.begin():
        user = session.scalar(select(User).where(User.role == "ADMIN"))
        user.is_active = False
    assert catalog_client.get("/api/v1/products", headers=admin_headers).status_code == 401
