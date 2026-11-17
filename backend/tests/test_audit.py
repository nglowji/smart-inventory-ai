import json
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from test_inventory import balance, move, new_product

from app.db.models import AuditLog, User

pytestmark = pytest.mark.integration


def test_failed_login_audit_survives_401_and_hides_credentials(catalog_client, admin_headers):
    correlation = str(uuid4())
    password = "do-not-store-this-password"
    response = catalog_client.post(
        "/api/v1/auth/login",
        headers={"X-Request-ID": correlation},
        json={
            "email": "absent@example.com",
            "password": password,
        },
    )
    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == correlation
    assert response.json()["error"]["request_id"] == correlation
    logs = catalog_client.get("/api/v1/audit?event_type=LOGIN_FAILED", headers=admin_headers)
    assert logs.status_code == 200
    result = logs.json()
    assert result["total"] == 1
    event = result["items"][0]
    assert event["actor_id"] is None
    assert event["request_id"] == correlation
    assert event["details"] == {"reason": "invalid_credentials"}
    assert password not in logs.text
    assert "absent@example.com" not in logs.text
    assert "password_hash" not in logs.text


def test_archive_and_adjustment_audit_is_actor_scoped_and_not_duplicated(
    catalog_client, admin_headers
):
    product = new_product(catalog_client, admin_headers)
    assert move(catalog_client, admin_headers, product, "IN", "10").status_code == 201
    key = str(uuid4())
    result = move(catalog_client, admin_headers, product, "ADJUST_OUT", "1", key=key)
    assert result.status_code == 201
    assert (
        move(catalog_client, admin_headers, product, "ADJUST_OUT", "1", key=key).status_code == 200
    )
    assert (
        catalog_client.post(
            f"/api/v1/products/{product['id']}/archive", headers=admin_headers
        ).status_code
        == 200
    )
    assert (
        catalog_client.post(
            f"/api/v1/products/{product['id']}/archive", headers=admin_headers
        ).status_code
        == 200
    )
    logs = catalog_client.get(
        "/api/v1/audit?event_type=STOCK_ADJUSTED", headers=admin_headers
    ).json()
    assert logs["total"] == 1
    assert logs["items"][0]["actor_email"] == "admin@example.com"
    assert logs["items"][0]["target_id"] == result.json()["id"]
    assert logs["items"][0]["details"]["quantity"] == "1.000"
    assert (
        catalog_client.get(
            "/api/v1/audit?event_type=PRODUCT_ARCHIVED", headers=admin_headers
        ).json()["total"]
        == 1
    )


def test_audit_failure_rolls_back_adjustment(catalog_client, admin_headers, catalog_db):
    product = new_product(catalog_client, admin_headers)
    assert move(catalog_client, admin_headers, product, "IN", "10").status_code == 201
    with catalog_db.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE audit_logs ADD CONSTRAINT test_block_adjust_audit "
                "CHECK (event_type != 'STOCK_ADJUSTED')"
            )
        )
    assert move(catalog_client, admin_headers, product, "ADJUST_IN", "3").status_code == 409
    assert balance(catalog_client, admin_headers, product) == "10.000"
    assert catalog_client.get("/api/v1/stock/movements", headers=admin_headers).json()["total"] == 1


def test_account_creation_rolls_back_when_audit_fails(catalog_client, admin_headers, catalog_db):
    with catalog_db.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE audit_logs ADD CONSTRAINT test_block_user_audit "
                "CHECK (event_type != 'USER_CREATED')"
            )
        )
    response = catalog_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "blocked@example.com",
            "password": "initial-password-123",
            "role": "VIEWER",
        },
    )
    assert response.status_code == 409
    with Session(catalog_db) as session:
        assert session.scalar(select(User).where(User.email == "blocked@example.com")) is None


def test_audit_api_is_read_only_and_paginated(catalog_client, admin_headers, catalog_db):
    response = catalog_client.get("/api/v1/audit?page_size=1", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 1
    event_id = response.json()["items"][0]["id"]
    assert UUID(event_id)
    with Session(catalog_db) as session:
        previous = session.scalar(select(func.count()).select_from(AuditLog))
    for method in (catalog_client.patch, catalog_client.delete):
        assert method(f"/api/v1/audit/{event_id}", headers=admin_headers).status_code in (404, 405)
    with Session(catalog_db) as session:
        assert session.scalar(select(func.count()).select_from(AuditLog)) == previous
        assert not any(
            "initial-password" in json.dumps(row.details)
            for row in session.scalars(select(AuditLog))
        )
