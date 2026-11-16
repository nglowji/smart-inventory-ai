from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy.orm import Session
from test_inventory import move, new_product

from app.db.models import StockMovement

pytestmark = pytest.mark.integration


def test_dashboard_matches_uat_and_separates_units(catalog_client, admin_headers):
    cases = [
        ("SP001", "PCS", "10", "3500", "30", "18"),
        ("SP002", "PCS", "20", "12000", "50", "35"),
        ("SP003", "PCS", "5", "65000", "10", "2"),
        ("SP004", "LITER", "2", "350000", "5", "3.5"),
        ("SP005", "PCS", "0", "1000", "100", "0"),
    ]
    products = []
    for sku, unit, minimum, cost, incoming, outgoing in cases:
        p = new_product(
            catalog_client, admin_headers, sku=sku, unit=unit, min_stock=minimum, cost=cost
        )
        products.append(p)
        assert move(catalog_client, admin_headers, p, "IN", incoming).status_code == 201
        if outgoing != "0":
            assert move(catalog_client, admin_headers, p, "OUT", outgoing).status_code == 201
    summary = catalog_client.get("/api/v1/dashboard/summary", headers=admin_headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["total_active_skus"] == 5
    assert summary.json()["low_stock_count"] == 2
    assert summary.json()["estimated_inventory_value_vnd"] == "1367000.00"
    assert summary.json()["movement_count"] == 9
    assert summary.json()["stock_by_unit"] == {"PCS": "135.000", "KG": "0.000", "LITER": "1.500"}
    low = catalog_client.get("/api/v1/stock/balances?low_stock=true", headers=admin_headers).json()
    assert [p["sku"] for p in low["items"]] == ["SP002", "SP004"]
    assert move(catalog_client, admin_headers, products[0], "ADJUST_OUT", "1").status_code == 201
    flow = catalog_client.get("/api/v1/dashboard/flow", headers=admin_headers)
    assert flow.status_code == 200, flow.text
    assert flow.json()["totals"]["PCS"] == {"inbound": "190.000", "outbound": "55.000"}
    assert flow.json()["totals"]["LITER"] == {"inbound": "5.000", "outbound": "3.500"}
    catalog_client.post(f"/api/v1/products/{products[1]['id']}/archive", headers=admin_headers)
    summary = catalog_client.get("/api/v1/dashboard/summary", headers=admin_headers).json()
    assert summary["low_stock_count"] == 1
    assert summary["total_active_skus"] == 4
    assert summary["estimated_inventory_value_vnd"] == "1363500.00"


def test_local_day_boundaries(catalog_client, admin_headers, catalog_db):
    product = new_product(catalog_client, admin_headers)
    earlier = move(catalog_client, admin_headers, product, "IN", "2").json()
    later = move(catalog_client, admin_headers, product, "IN", "3").json()
    with Session(catalog_db) as session, session.begin():
        session.get(StockMovement, UUID(earlier["id"])).occurred_at = datetime(
            2026, 11, 15, 16, 59, tzinfo=UTC
        )
        session.get(StockMovement, UUID(later["id"])).occurred_at = datetime(
            2026, 11, 15, 17, 0, tzinfo=UTC
        )
    params = "date_from=2026-11-16&date_to=2026-11-16"
    history = catalog_client.get(f"/api/v1/stock/movements?{params}", headers=admin_headers).json()
    assert history["total"] == 1
    assert history["items"][0]["id"] == later["id"]
    flow = catalog_client.get(f"/api/v1/dashboard/flow?{params}", headers=admin_headers).json()
    assert flow["items"][0]["date"] == "2026-11-16"
    assert flow["totals"]["PCS"]["inbound"] == "3.000"


def test_empty_reports_and_invalid_ranges(catalog_client, admin_headers):
    summary = catalog_client.get("/api/v1/dashboard/summary", headers=admin_headers).json()
    assert summary["total_active_skus"] == 0
    assert summary["estimated_inventory_value_vnd"] == "0.00"
    assert catalog_client.get("/api/v1/dashboard/flow", headers=admin_headers).json()["items"] == []
    for path in ("/dashboard/summary", "/dashboard/flow", "/stock/movements"):
        response = catalog_client.get(
            f"/api/v1{path}?date_from=2026-11-17&date_to=2026-11-16", headers=admin_headers
        )
        assert response.status_code == 422
    assert catalog_client.get("/api/v1/dashboard/summary").status_code == 401
