from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.db.models import AuditLog, Category, Product, StockBalance, StockMovement
from app.demo import seed
from app.demo.dataset import PRODUCTS, entity_id
from app.demo.planning import plan_product, preview
from app.modules.ai.tools import execute_tool

NOW = datetime(2026, 11, 17, 3, tzinfo=UTC)


def test_demo_plan_has_variety_and_reconciles_each_ledger():
    anchor = NOW - timedelta(hours=4)
    for index, spec in enumerate(PRODUCTS):
        movements = plan_product(spec, index, anchor)
        balance = Decimal(0)
        for movement in movements:
            assert movement.before == balance
            assert movement.after >= 0
            assert movement.occurred_at < NOW
            assert movement.reason.startswith("[DEMO]")
            if spec.unit == "PCS":
                assert movement.quantity == movement.quantity.to_integral_value()
            balance = movement.after
        assert balance == spec.target
    report = preview(anchor)
    assert report["products"] == 36
    assert report["active_products"] == 34
    assert report["movements"] == 1674
    assert report["low_stock"] == 11
    assert set(report["movement_types"]) == {"IN", "OUT", "ADJUST_IN", "ADJUST_OUT"}


@pytest.mark.integration
def test_demo_import_and_repeat_preserve_user_changes(catalog_client, catalog_db, admin_headers):
    with Session(catalog_db) as session:
        report = seed.import_demo(session, "admin@example.com", now=NOW)
    assert report["status"] == "imported"
    summary = catalog_client.get("/api/v1/dashboard/summary", headers=admin_headers).json()
    assert summary["total_active_skus"] == report["active_products"]
    assert summary["low_stock_count"] == report["low_stock"]
    assert summary["estimated_inventory_value_vnd"] == report["estimated_inventory_value_vnd"]
    assert summary["stock_by_unit"] == report["stock_by_unit"]
    with Session(catalog_db) as session, session.begin():
        session.get(Product, entity_id("product:DEMO-VP001")).name = "User edited this product"
    with Session(catalog_db) as session:
        repeated = seed.import_demo(session, "admin@example.com", now=NOW + timedelta(days=1))
    assert repeated["status"] == "already_imported"
    with Session(catalog_db) as session:
        assert session.scalar(select(func.count()).select_from(StockMovement)) == 1674
        assert (
            session.get(Product, entity_id("product:DEMO-VP001")).name == "User edited this product"
        )
        for spec in PRODUCTS:
            assert (
                session.get(StockBalance, entity_id("product:" + spec.sku)).on_hand == spec.target
            )
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.event_type == "DEMO_DATA_IMPORTED")
            )
            == 1
        )
    audit = catalog_client.get("/api/v1/audit?event_type=DEMO_DATA_IMPORTED", headers=admin_headers)
    assert audit.status_code == 200
    assert audit.json()["items"][0]["details"]["movements"] == 1674
    fallback = execute_tool(catalog_db, "recommend_replenishment", {"sku": "DEMO-VP006"})
    assert fallback["data"]["insufficient_history"] is True
    assert fallback["data"]["suggested_qty"] == "10"


@pytest.mark.integration
def test_demo_collision_does_not_overwrite_existing_data(catalog_client, catalog_db, admin_headers):
    response = catalog_client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "sku": "DEMO-VP001",
            "name": "Existing user product",
            "unit": "PCS",
        },
    )
    assert response.status_code == 201
    with Session(catalog_db) as session, pytest.raises(DomainError) as caught:
        seed.import_demo(session, "admin@example.com", now=NOW)
    assert caught.value.code == "DEMO_NAMESPACE_CONFLICT"
    with Session(catalog_db) as session:
        assert session.scalar(select(func.count()).select_from(Product)) == 1
        assert session.scalar(select(func.count()).select_from(Category)) == 0
        assert session.scalar(select(Product.name)) == "Existing user product"


@pytest.mark.integration
def test_demo_audit_failure_rolls_back_entire_import(catalog_client, catalog_db, monkeypatch):
    original = seed.record_event

    def failing(session, event, **kwargs):
        if event == "DEMO_DATA_IMPORTED":
            raise RuntimeError("Simulated final audit failure")
        return original(session, event, **kwargs)

    monkeypatch.setattr(seed, "record_event", failing)
    with Session(catalog_db) as session, pytest.raises(RuntimeError):
        seed.import_demo(session, "admin@example.com", now=NOW)
    with Session(catalog_db) as session:
        for model in [Product, Category, StockMovement, StockBalance, AuditLog]:
            assert session.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.integration
def test_staff_cannot_import_demo_dataset(catalog_client, catalog_db):
    with Session(catalog_db) as session, pytest.raises(DomainError) as caught:
        seed.import_demo(session, "staff@example.com", now=NOW)
    assert caught.value.status == 403
