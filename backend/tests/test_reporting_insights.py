from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.orm import Session
from test_inventory import move, new_product, role_headers

from app.db.models import StockMovement

pytestmark = pytest.mark.integration


def test_insights_empty_and_read_permissions(catalog_client):
    assert catalog_client.get("/api/v1/dashboard/insights").status_code == 401
    for role in ["ADMIN", "STAFF", "VIEWER"]:
        response = catalog_client.get(
            "/api/v1/dashboard/insights", headers=role_headers(catalog_client, role)
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["health"] == {"healthy": 0, "low": 0, "out_of_stock": 0}
        assert data["category_values"] == []
        assert data["top_outbound"] == {"PCS": [], "KG": [], "LITER": []}


def test_health_buckets_are_disjoint_and_category_value_includes_archived(
    catalog_client, admin_headers
):
    profiles = [
        ("FULL", "10", "20"),
        ("LOW", "10", "3"),
        ("EMPTY", "10", "0"),
        ("NO-MIN", "0", "2"),
        ("OLD", "10", "5"),
    ]
    for sku, minimum, incoming in profiles:
        product = new_product(
            catalog_client, admin_headers, sku=sku, min_stock=minimum, cost="1000"
        )
        if incoming != "0":
            move(catalog_client, admin_headers, product, "IN", incoming)
        if sku == "OLD":
            catalog_client.post(f"/api/v1/products/{product['id']}/archive", headers=admin_headers)
    data = catalog_client.get("/api/v1/dashboard/insights", headers=admin_headers).json()
    assert data["health"] == {"healthy": 2, "low": 1, "out_of_stock": 1}
    assert data["archived_skus"] == 1
    assert data["without_outbound_skus"] == 4
    assert data["estimated_inventory_value_vnd"] == "30000.00"
    assert data["category_values"][0]["name"] == "Chưa phân loại"
    assert data["category_values"][0]["sku_count"] == 5


def test_category_chart_remainder_preserves_every_sku_and_fractional_value(
    catalog_client, admin_headers, catalog_db
):
    for index in range(9):
        category = catalog_client.post(
            "/api/v1/categories", headers=admin_headers, json={"name": f"Group {index}"}
        ).json()
        product = new_product(
            catalog_client, admin_headers, sku=f"P{index}", unit="KG", cost="0.01"
        )
        catalog_client.patch(
            f"/api/v1/products/{product['id']}",
            headers=admin_headers,
            json={"category_id": category["id"]},
        )
        move(catalog_client, admin_headers, product, "IN", "0.4")
    data = catalog_client.get("/api/v1/dashboard/insights", headers=admin_headers).json()
    assert len(data["category_values"]) == 7
    assert data["category_values"][-1]["key"] == "other"
    assert sum(row["sku_count"] for row in data["category_values"]) == 9
    assert sum(Decimal(row["value_vnd"]) for row in data["category_values"]) == Decimal("0.036")
    summary = catalog_client.get("/api/v1/dashboard/summary", headers=admin_headers).json()
    assert (
        data["estimated_inventory_value_vnd"] == summary["estimated_inventory_value_vnd"] == "0.04"
    )


def test_period_activity_counts_all_types_and_ranks_only_out_per_unit(
    catalog_client, admin_headers, catalog_db
):
    first = new_product(catalog_client, admin_headers, sku="PCS-ONE")
    second = new_product(catalog_client, admin_headers, sku="PCS-TWO")
    kg = new_product(catalog_client, admin_headers, sku="KG-ONE", unit="KG")
    created = []
    for product, quantity in [(first, "2"), (second, "4"), (kg, "3.125")]:
        created.append(move(catalog_client, admin_headers, product, "IN", "10").json())
        created.append(move(catalog_client, admin_headers, product, "OUT", quantity).json())
    created.append(move(catalog_client, admin_headers, first, "ADJUST_OUT", "6").json())
    with Session(catalog_db) as session, session.begin():
        for item in created:
            session.get(StockMovement, UUID(item["id"])).occurred_at = datetime(
                2026, 11, 15, 17, 0, tzinfo=UTC
            )
    path = "/api/v1/dashboard/insights?date_from=2026-11-16&date_to=2026-11-16"
    data = catalog_client.get(path, headers=admin_headers).json()
    assert data["daily_activity"] == [{"date": "2026-11-16", "count": 7}]
    assert {row["movement_type"]: row["count"] for row in data["movement_types"]} == {
        "IN": 3,
        "OUT": 3,
        "ADJUST_IN": 0,
        "ADJUST_OUT": 1,
    }
    assert [row["sku"] for row in data["top_outbound"]["PCS"]] == ["PCS-TWO", "PCS-ONE"]
    assert data["top_outbound"]["PCS"][1]["quantity"] == "2.000"
    assert data["top_outbound"]["KG"][0]["quantity"] == "3.125"
    assert data["without_outbound_skus"] == 0
    empty = catalog_client.get(
        "/api/v1/dashboard/insights?date_from=2026-11-15&date_to=2026-11-15", headers=admin_headers
    ).json()
    assert empty["daily_activity"] == []
    assert empty["without_outbound_skus"] == 3
    assert empty["health"] == data["health"]  # Current stock is independent of period filters.
    invalid = catalog_client.get(
        "/api/v1/dashboard/insights?date_from=2026-11-17&date_to=2026-11-16", headers=admin_headers
    )
    assert invalid.status_code == 422
