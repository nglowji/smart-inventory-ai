from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.models import StockBalance, StockMovement

pytestmark = pytest.mark.integration


def new_product(client, headers, *, sku="STOCK001", unit="PCS", min_stock="0", cost="0"):
    response = client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "sku": sku,
            "name": sku,
            "unit": unit,
            "min_stock": min_stock,
            "unit_cost_vnd": cost,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def move(
    client, headers, product, kind, quantity, *, key=None, reason="Giao dịch kiểm thử", **extra
):
    return client.post(
        "/api/v1/stock/movements",
        headers={
            **headers,
            "Idempotency-Key": key or str(uuid4()),
        },
        json={
            "product_id": product["id"],
            "movement_type": kind,
            "quantity": quantity,
            "reason": reason,
            **extra,
        },
    )


def balance(client, headers, product):
    return client.get(f"/api/v1/products/{product['id']}", headers=headers).json()["on_hand"]


def role_headers(client, role):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"{role.lower()}@example.com",
            "password": "test-password-123",
        },
    )
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_in_out_and_snapshot(catalog_client, admin_headers):
    p = new_product(catalog_client, admin_headers)
    incoming = move(catalog_client, admin_headers, p, "IN", "10")
    assert incoming.status_code == 201
    assert incoming.json()["stock_before"] == "0.000"
    assert incoming.json()["stock_after"] == "10.000"
    outgoing = move(catalog_client, admin_headers, p, "OUT", "4")
    assert outgoing.status_code == 201
    assert outgoing.json()["stock_before"] == "10.000"
    assert outgoing.json()["stock_after"] == "6.000"
    assert balance(catalog_client, admin_headers, p) == "6.000"
    assert outgoing.json()["actor_email"] == "admin@example.com"


def test_insufficient_stock_does_not_write(catalog_client, admin_headers):
    p = new_product(catalog_client, admin_headers)
    move(catalog_client, admin_headers, p, "IN", "10")
    response = move(catalog_client, admin_headers, p, "OUT", "11")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK"
    assert balance(catalog_client, admin_headers, p) == "10.000"
    assert catalog_client.get("/api/v1/stock/movements", headers=admin_headers).json()["total"] == 1


@pytest.mark.parametrize("value", ["0", "-1", "1.0001", "NaN", 1, "1.5"])
def test_invalid_quantity(catalog_client, admin_headers, value):
    p = new_product(catalog_client, admin_headers)
    assert move(catalog_client, admin_headers, p, "IN", value).status_code == 422
    assert balance(catalog_client, admin_headers, p) == "0.000"


def test_decimal_stock_and_unit_rules(catalog_client, admin_headers):
    p = new_product(catalog_client, admin_headers, unit="LITER")
    move(catalog_client, admin_headers, p, "IN", "0.300")
    move(catalog_client, admin_headers, p, "OUT", "0.100")
    assert balance(catalog_client, admin_headers, p) == "0.200"


def test_retry_is_canonical_and_conflicts(catalog_client, admin_headers):
    p = new_product(catalog_client, admin_headers)
    key = str(uuid4())
    first = move(catalog_client, admin_headers, p, "IN", "5", key=key)
    repeat = move(catalog_client, admin_headers, p, "IN", "5.000", key=key)
    assert first.status_code == 201
    assert repeat.status_code == 200
    assert first.json()["id"] == repeat.json()["id"]
    assert first.json()["actor_email"] == repeat.json()["actor_email"]
    conflict = move(catalog_client, admin_headers, p, "IN", "6", key=key)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert balance(catalog_client, admin_headers, p) == "5.000"


def test_concurrent_out_never_negative(catalog_client, admin_headers):
    p = new_product(catalog_client, admin_headers)
    move(catalog_client, admin_headers, p, "IN", "10")
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: move(catalog_client, admin_headers, p, "OUT", "8"), range(2))
        )
    assert sorted(r.status_code for r in results) == [201, 409]
    assert balance(catalog_client, admin_headers, p) == "2.000"


def test_concurrent_retry_out_succeeds_once(catalog_client, admin_headers):
    p = new_product(catalog_client, admin_headers)
    move(catalog_client, admin_headers, p, "IN", "10")
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: move(catalog_client, admin_headers, p, "OUT", "8", key=key), range(2)
            )
        )
    assert sorted(r.status_code for r in results) == [200, 201]
    assert len({r.json()["id"] for r in results}) == 1
    assert balance(catalog_client, admin_headers, p) == "2.000"


def test_cross_product_duplicate_key_rolls_back_losing_balance(catalog_client, admin_headers):
    a = new_product(catalog_client, admin_headers, sku="A")
    b = new_product(catalog_client, admin_headers, sku="B")
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda p: move(catalog_client, admin_headers, p, "IN", "5", key=key), [a, b]
            )
        )
    assert sorted(r.status_code for r in results) == [201, 409]
    assert sorted(
        [balance(catalog_client, admin_headers, a), balance(catalog_client, admin_headers, b)]
    ) == ["0.000", "5.000"]


def test_adjustments_roles_reasons_and_archived(catalog_client, admin_headers):
    p = new_product(catalog_client, admin_headers)
    staff = role_headers(catalog_client, "STAFF")
    viewer = role_headers(catalog_client, "VIEWER")
    assert move(catalog_client, viewer, p, "IN", "2").status_code == 403
    assert move(catalog_client, staff, p, "ADJUST_IN", "2").status_code == 403
    assert move(catalog_client, staff, p, "IN", "2").status_code == 201
    assert (
        move(catalog_client, admin_headers, p, "ADJUST_IN", "1", reason="short").status_code == 422
    )
    assert move(catalog_client, admin_headers, p, "OUT", "1", reason=" ").status_code == 422
    assert move(catalog_client, admin_headers, p, "ADJUST_OUT", "3").status_code == 409
    assert move(catalog_client, admin_headers, p, "ADJUST_IN", "1").status_code == 201
    catalog_client.post(f"/api/v1/products/{p['id']}/archive", headers=admin_headers)
    response = move(catalog_client, admin_headers, p, "IN", "1")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PRODUCT_ARCHIVED"


def test_movement_insert_failure_rolls_back_balance(catalog_client, admin_headers, catalog_db):
    p = new_product(catalog_client, admin_headers)
    with catalog_db.begin() as connection:
        connection.execute(
            text("ALTER TABLE stock_movements ADD CONSTRAINT test_failure CHECK (false)")
        )
    response = move(catalog_client, admin_headers, p, "IN", "5")
    assert response.status_code == 409
    with Session(catalog_db) as session:
        assert session.get(StockBalance, UUID(p["id"])).on_hand == 0
        assert session.scalar(select(func.count()).select_from(StockMovement)) == 0


def test_history_filters_and_immutability(catalog_client, admin_headers):
    a = new_product(catalog_client, admin_headers, sku="A")
    b = new_product(catalog_client, admin_headers, sku="B")
    movement = move(catalog_client, admin_headers, a, "IN", "10").json()
    move(catalog_client, admin_headers, b, "IN", "5")
    move(catalog_client, admin_headers, a, "OUT", "1")
    result = catalog_client.get(
        "/api/v1/stock/movements?sku=a&movement_type=IN", headers=admin_headers
    ).json()
    assert result["total"] == 1
    assert result["items"][0]["id"] == movement["id"]
    for method in (catalog_client.patch, catalog_client.delete):
        assert method(
            f"/api/v1/stock/movements/{movement['id']}", headers=admin_headers
        ).status_code in (404, 405)
    assert (
        catalog_client.get(
            "/api/v1/stock/movements?page_size=1&page=2", headers=admin_headers
        ).json()["total"]
        == 3
    )
