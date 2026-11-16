from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from conftest import migration_config
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from alembic import command
from app.db.models import Product, StockBalance, StockMovement, User

pytestmark = pytest.mark.integration


def product_payload(**changes):
    return {
        "sku": " sp001 ",
        "name": "Bút bi xanh",
        "unit": "PCS",
        "min_stock": "10",
        "unit_cost_vnd": "3500.00",
        **changes,
    }


def create_product(client, headers, **changes):
    response = client.post("/api/v1/products", headers=headers, json=product_payload(**changes))
    assert response.status_code == 201, response.text
    return response.json()


def test_product_and_balance_created_together(catalog_client, admin_headers, catalog_db):
    result = create_product(catalog_client, admin_headers)
    assert result["sku"] == "SP001"
    assert result["on_hand"] == "0.000"
    assert result["min_stock"] == "10.000"
    assert result["unit_cost_vnd"] == "3500.00"
    with Session(catalog_db) as session:
        assert session.scalar(select(func.count()).select_from(Product)) == 1
        assert session.get(StockBalance, UUID(result["id"])).on_hand == Decimal("0")


def test_balance_insert_failure_rolls_back_product(catalog_client, admin_headers, catalog_db):
    with catalog_db.begin() as connection:
        connection.execute(
            text("ALTER TABLE stock_balances ADD CONSTRAINT test_fail_balance CHECK (false)")
        )
    response = catalog_client.post(
        "/api/v1/products", headers=admin_headers, json=product_payload()
    )
    assert response.status_code == 409
    with Session(catalog_db) as session:
        assert session.scalar(select(func.count()).select_from(Product)) == 0


def test_duplicate_sku_even_after_archive(catalog_client, admin_headers):
    product = create_product(catalog_client, admin_headers)
    assert (
        catalog_client.post(
            f"/api/v1/products/{product['id']}/archive", headers=admin_headers
        ).status_code
        == 200
    )
    response = catalog_client.post(
        "/api/v1/products", headers=admin_headers, json=product_payload(sku="sp001")
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SKU_ALREADY_EXISTS"
    assert (
        catalog_client.get(f"/api/v1/products/{product['id']}", headers=admin_headers).json()[
            "is_active"
        ]
        is False
    )


def test_concurrent_duplicate_sku_uses_db_unique_constraint(catalog_client, admin_headers):
    def post_product(_):
        return catalog_client.post(
            "/api/v1/products", headers=admin_headers, json=product_payload()
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(post_product, range(2)))
    assert sorted(r.status_code for r in responses) == [201, 409]
    conflict = next(r for r in responses if r.status_code == 409)
    assert conflict.json()["error"]["code"] == "SKU_ALREADY_EXISTS"


@pytest.mark.parametrize(
    "changes",
    [
        {"min_stock": "-1"},
        {"min_stock": "0.0001"},
        {"unit_cost_vnd": "-1"},
        {"unit_cost_vnd": "1.001"},
        {"unit": "BOX"},
        {"name": "   "},
        {"sku": " "},
        {"lead_time_days": -1},
        {"lead_time_days": 1.5},
        {"on_hand": "100"},
        {"min_stock": "NaN"},
        {"min_stock": "100000000000"},
        {"min_stock": 10},
        {"unit_cost_vnd": 3500.0},
    ],
)
def test_product_validation(catalog_client, admin_headers, changes):
    response = catalog_client.post(
        "/api/v1/products", headers=admin_headers, json=product_payload(**changes)
    )
    assert response.status_code == 422, response.text


def test_catalog_relations_and_patch(catalog_client, admin_headers):
    category = catalog_client.post(
        "/api/v1/categories", headers=admin_headers, json={"name": " Văn phòng phẩm "}
    ).json()
    supplier = catalog_client.post(
        "/api/v1/suppliers",
        headers=admin_headers,
        json={"name": "Nhà cung cấp A", "phone": "0900000000", "email": "vendor@example.com"},
    ).json()
    product = create_product(
        catalog_client,
        admin_headers,
        category_id=category["id"],
        default_supplier_id=supplier["id"],
    )
    assert category["name"] == "Văn phòng phẩm"
    duplicate = catalog_client.post(
        "/api/v1/categories", headers=admin_headers, json={"name": "Văn phòng phẩm"}
    )
    assert duplicate.status_code == 409
    response = catalog_client.patch(
        f"/api/v1/products/{product['id']}",
        headers=admin_headers,
        json={"name": "Tên mới", "category_id": None, "unit": "KG"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["category_id"] is None
    assert response.json()["unit"] == "KG"
    supplier_patch = catalog_client.patch(
        f"/api/v1/suppliers/{supplier['id']}", headers=admin_headers, json={"phone": None}
    )
    assert supplier_patch.status_code == 200
    assert supplier_patch.json()["phone"] is None
    assert catalog_client.get("/api/v1/suppliers", headers=admin_headers).json()["total"] == 1
    assert catalog_client.get("/api/v1/categories", headers=admin_headers).json()["total"] == 1


def test_missing_and_inactive_references(catalog_client, admin_headers):
    response = catalog_client.post(
        "/api/v1/products", headers=admin_headers, json=product_payload(category_id=str(uuid4()))
    )
    assert response.status_code == 422
    category = catalog_client.post(
        "/api/v1/categories", headers=admin_headers, json={"name": "Archived"}
    ).json()
    assert (
        catalog_client.patch(
            f"/api/v1/categories/{category['id']}", headers=admin_headers, json={"is_active": False}
        ).status_code
        == 200
    )
    response = catalog_client.post(
        "/api/v1/products", headers=admin_headers, json=product_payload(category_id=category["id"])
    )
    assert response.status_code == 422


def test_filter_pagination_and_archive(catalog_client, admin_headers):
    first = create_product(catalog_client, admin_headers)
    create_product(catalog_client, admin_headers, sku="SP002", name="Mực in", unit="LITER")
    response = catalog_client.get("/api/v1/products?page_size=1", headers=admin_headers)
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["sku"] == "SP001"
    assert (
        catalog_client.get("/api/v1/products?search=mực", headers=admin_headers).json()["items"][0][
            "sku"
        ]
        == "SP002"
    )
    assert (
        catalog_client.get("/api/v1/products?search=%", headers=admin_headers).json()["total"] == 0
    )
    assert (
        catalog_client.get("/api/v1/products?page_size=101", headers=admin_headers).status_code
        == 422
    )
    catalog_client.post(f"/api/v1/products/{first['id']}/archive", headers=admin_headers)
    assert (
        catalog_client.get("/api/v1/products?active=true", headers=admin_headers).json()["total"]
        == 1
    )
    assert (
        catalog_client.get("/api/v1/products?active=false", headers=admin_headers).json()["total"]
        == 1
    )


def test_unit_immutable_with_history_even_when_balance_zero(
    catalog_client, admin_headers, catalog_db
):
    product = create_product(catalog_client, admin_headers)
    with Session(catalog_db) as session, session.begin():
        actor = session.scalar(select(User.id).where(User.role == "ADMIN"))
        # A complete fixture cycle returns balance to zero; history still forbids changing unit.
        for kind, before, after in (("IN", 0, 1), ("OUT", 1, 0)):
            session.add(
                StockMovement(
                    product_id=UUID(product["id"]),
                    actor_id=actor,
                    movement_type=kind,
                    quantity=1,
                    stock_before=before,
                    stock_after=after,
                    reason="Fixture cycle",
                    idempotency_key=str(uuid4()),
                    request_fingerprint="0" * 64,
                )
            )
    response = catalog_client.patch(
        f"/api/v1/products/{product['id']}", headers=admin_headers, json={"unit": "KG"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "UNIT_IMMUTABLE"
    assert (
        catalog_client.patch(
            f"/api/v1/products/{product['id']}", headers=admin_headers, json={"unit": "PCS"}
        ).status_code
        == 200
    )
    catalog_client.post(f"/api/v1/products/{product['id']}/archive", headers=admin_headers)
    with Session(catalog_db) as session:
        assert session.scalar(select(func.count()).select_from(StockMovement)) == 2
        assert session.get(StockBalance, UUID(product["id"])) is not None


@pytest.mark.parametrize(
    "payload",
    [{"name": None}, {"unit": None}, {"min_stock": None}, {"on_hand": "1"}, {"is_active": True}],
)
def test_product_patch_rejects_invalid_fields(catalog_client, admin_headers, payload):
    product = create_product(catalog_client, admin_headers)
    response = catalog_client.patch(
        f"/api/v1/products/{product['id']}", headers=admin_headers, json=payload
    )
    assert response.status_code == 422


def test_not_found_and_no_hard_delete(catalog_client, admin_headers):
    response = catalog_client.get(f"/api/v1/products/{uuid4()}", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"
    product = create_product(catalog_client, admin_headers)
    assert (
        catalog_client.delete(
            f"/api/v1/products/{product['id']}", headers=admin_headers
        ).status_code
        == 405
    )


def test_migration_downgrade_and_upgrade(catalog_db):
    with catalog_db.begin() as connection:
        command.downgrade(migration_config(connection), "base")
        assert "products" not in inspect(connection).get_table_names()
        command.upgrade(migration_config(connection), "head")
        command.check(migration_config(connection))
        assert {"products", "stock_balances", "categories", "suppliers", "users"} <= set(
            inspect(connection).get_table_names()
        )
