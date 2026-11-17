import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.db.models import User
from app.main import create_app
from app.modules.auth.service import passwords

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolate_application_environment(monkeypatch):
    # Runtime secrets/settings must not make tests connect to the application's DB.
    # Integration fixtures only use the explicitly configured TEST_DATABASE_URL.
    for name in tuple(os.environ):
        if name.lower() in Settings.model_fields:
            monkeypatch.delenv(name)


def migration_config(connection):
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


@pytest.fixture(scope="session")
def test_password_hash():
    return passwords.hash("test-password-123")


@pytest.fixture
def catalog_db():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL for PostgreSQL integration tests")
    parsed = make_url(url)
    if parsed.drivername != "postgresql+psycopg" or not parsed.database.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must point to a dedicated PostgreSQL database ending _test")
    # Every test gets an isolated schema, including alembic_version. Never drop public tables.
    schema = "test_" + uuid4().hex
    admin_engine = create_engine(url)
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.begin() as connection:
            command.upgrade(migration_config(connection), "head")
        yield engine
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


@pytest.fixture
def catalog_client(catalog_db, test_password_hash):
    with Session(catalog_db) as session, session.begin():
        for role in ("ADMIN", "STAFF", "VIEWER"):
            session.add(
                User(
                    email=f"{role.lower()}@example.com", role=role, password_hash=test_password_hash
                )
            )
    config = Settings(_env_file=None, jwt_secret="test-only-signing-secret-at-least-32-characters")
    with TestClient(create_app(config)) as client:
        # The app's startup engine is unused; session/health resolve the isolated test engine.
        client.app.state.engine = catalog_db
        yield client


@pytest.fixture
def admin_headers(catalog_client):
    response = catalog_client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": "test-password-123",
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}
