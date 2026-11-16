from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_inventory import balance, move, new_product, role_headers

from app.db.models import StockMovement

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("reason", [None, "", "   ", "short"])
def test_adjustment_reason_is_required(catalog_client, admin_headers, reason):
    product = new_product(catalog_client, admin_headers)
    assert (
        move(catalog_client, admin_headers, product, "ADJUST_IN", "1", reason=reason).status_code
        == 422
    )
    assert balance(catalog_client, admin_headers, product) == "0.000"


@pytest.mark.parametrize("field", ["actor_id", "stock_before", "stock_after", "on_hand"])
def test_client_cannot_forge_stock_or_actor(catalog_client, admin_headers, field):
    product = new_product(catalog_client, admin_headers)
    value = str(uuid4()) if field == "actor_id" else "999"
    response = move(catalog_client, admin_headers, product, "IN", "1", **{field: value})
    assert response.status_code == 422
    assert balance(catalog_client, admin_headers, product) == "0.000"


def test_retry_after_archive_returns_original_result(catalog_client, admin_headers):
    product = new_product(catalog_client, admin_headers)
    key = str(uuid4())
    first = move(catalog_client, admin_headers, product, "IN", "5", key=key)
    assert first.status_code == 201
    catalog_client.post(f"/api/v1/products/{product['id']}/archive", headers=admin_headers)
    repeated = move(catalog_client, admin_headers, product, "IN", "5", key=key)
    assert repeated.status_code == 200
    assert repeated.json() == first.json()
    assert balance(catalog_client, admin_headers, product) == "5.000"


def test_same_key_cannot_be_replayed_by_a_different_actor(catalog_client, admin_headers):
    product = new_product(catalog_client, admin_headers)
    key = str(uuid4())
    assert move(catalog_client, admin_headers, product, "IN", "2", key=key).status_code == 201
    response = move(
        catalog_client, role_headers(catalog_client, "STAFF"), product, "IN", "2", key=key
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert balance(catalog_client, admin_headers, product) == "2.000"


def test_missing_idempotency_key_is_rejected(catalog_client, admin_headers):
    product = new_product(catalog_client, admin_headers)
    response = catalog_client.post(
        "/api/v1/stock/movements",
        headers=admin_headers,
        json={
            "product_id": product["id"],
            "movement_type": "IN",
            "quantity": "2",
        },
    )
    assert response.status_code == 422


def test_supplier_reference_is_validated(catalog_client, admin_headers):
    product = new_product(catalog_client, admin_headers)
    supplier = catalog_client.post(
        "/api/v1/suppliers", headers=admin_headers, json={"name": "Supplier test"}
    ).json()
    assert (
        move(
            catalog_client, admin_headers, product, "IN", "2", supplier_id=supplier["id"]
        ).status_code
        == 201
    )
    catalog_client.patch(
        f"/api/v1/suppliers/{supplier['id']}", headers=admin_headers, json={"is_active": False}
    )
    assert (
        move(
            catalog_client, admin_headers, product, "IN", "1", supplier_id=supplier["id"]
        ).status_code
        == 422
    )
    assert (
        move(
            catalog_client, admin_headers, product, "OUT", "1", supplier_id=supplier["id"]
        ).status_code
        == 422
    )
    assert balance(catalog_client, admin_headers, product) == "2.000"


def test_history_open_date_bounds_and_actor_filter(catalog_client, admin_headers, catalog_db):
    product = new_product(catalog_client, admin_headers)
    staff = role_headers(catalog_client, "STAFF")
    older = move(catalog_client, admin_headers, product, "IN", "3").json()
    newer = move(catalog_client, staff, product, "OUT", "1").json()
    with Session(catalog_db) as session, session.begin():
        session.get(StockMovement, UUID(older["id"])).occurred_at = datetime(
            2026, 11, 14, 17, tzinfo=UTC
        )
        session.get(StockMovement, UUID(newer["id"])).occurred_at = datetime(
            2026, 11, 16, 17, tzinfo=UTC
        )
    viewer = role_headers(catalog_client, "VIEWER")
    after = catalog_client.get(
        "/api/v1/stock/movements?date_from=2026-11-16", headers=viewer
    ).json()
    assert [m["id"] for m in after["items"]] == [newer["id"]]
    before = catalog_client.get("/api/v1/stock/movements?date_to=2026-11-16", headers=viewer).json()
    assert [m["id"] for m in before["items"]] == [older["id"]]
    actor = catalog_client.get(
        f"/api/v1/stock/movements?actor_id={newer['actor_id']}", headers=viewer
    ).json()
    assert actor["total"] == 1
    assert actor["items"][0]["id"] == newer["id"]


def test_database_rejects_inconsistent_movement_snapshot(catalog_client, admin_headers, catalog_db):
    product = new_product(catalog_client, admin_headers)
    valid = move(catalog_client, admin_headers, product, "IN", "5").json()
    with Session(catalog_db) as session:
        session.add(
            StockMovement(
                product_id=UUID(product["id"]),
                actor_id=UUID(valid["actor_id"]),
                movement_type="IN",
                quantity=1,
                stock_before=5,
                stock_after=99,
                idempotency_key=str(uuid4()),
                request_fingerprint="0" * 64,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    assert balance(catalog_client, admin_headers, product) == "5.000"
