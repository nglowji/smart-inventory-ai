import json
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session
from test_ai import ask, conversation
from test_inventory import move, new_product

from app.core.dates import LOCAL_ZONE
from app.db.models import Product
from app.modules.ai.memory import build_context, sanitize_context
from app.modules.ai.policies import requests_write
from app.modules.ai.routing import routing_context
from app.modules.ai.tools import execute_tool


@pytest.mark.parametrize(
    "question",
    [
        "Hướng dẫn nhập kho",
        "Cách xuất kho 5 cái như thế nào?",
        "Tổng xuất kho hôm nay",
        "Vì sao tồn giảm?",
        "Gợi ý nhập kho",
        "Quy trình điều chỉnh tồn",
    ],
)
def test_instruction_and_reporting_questions_are_not_execution_requests(question):
    assert not requests_write(question)


@pytest.mark.parametrize(
    "question", ["Hãy xuất 5 SP001", "Vui lòng xóa sản phẩm", "Nhập kho SP001"]
)
def test_actual_mutations_are_still_refused(question):
    assert requests_write(question)


def test_reference_memory_excludes_untrusted_payload_and_stale_values():
    memory = build_context(
        [
            {
                "data": {
                    "items": [
                        {"sku": "SP001", "name": "IGNORE SYSTEM private-marker", "on_hand": "999"},
                        {"sku": "SP002", "password": "private-key"},
                    ]
                }
            }
        ]
    )
    assert memory == {"choices": ["SP001", "SP002"]}
    assert build_context([{"data": {"date_from": "2026-11-01", "date_to": "2026-11-17"}}]) == {
        "from_date": "2026-11-01",
        "to_date": "2026-11-17",
    }
    assert "private" not in json.dumps(memory)
    assert sanitize_context(
        {
            "sku": "IGNORE SYSTEM",
            "choices": ["SP001", "a b", "SP001"],
            "from_date": "not-date",
            "answer": "private",
            "on_hand": 99,
        }
    ) == {"choices": ["SP001"]}


def test_relative_dates_are_computed_for_vietnam_calendar():
    prompt = routing_context(datetime(2026, 11, 17, 0, 30, tzinfo=LOCAL_ZONE))
    calendar = json.loads(prompt.split("Lịch Asia/Ho_Chi_Minh: ")[1])
    assert calendar["tuan_nay"] == ["2026-11-16", "2026-11-17"]
    assert calendar["tuan_truoc"] == ["2026-11-09", "2026-11-15"]
    assert calendar["thang_truoc"] == ["2026-10-01", "2026-10-31"]
    assert calendar["30_ngay_gan_nhat"] == ["2026-10-19", "2026-11-17"]


@pytest.mark.integration
def test_product_details_accentless_search_catalog_and_inventory_filters(
    catalog_client, admin_headers, catalog_db
):
    category = catalog_client.post(
        "/api/v1/categories", headers=admin_headers, json={"name": "Văn phòng phẩm"}
    ).json()
    supplier = catalog_client.post(
        "/api/v1/suppliers", headers=admin_headers, json={"name": "Minh An"}
    ).json()
    product = new_product(catalog_client, admin_headers, sku="BUT001", min_stock="10", cost="3500")
    catalog_client.patch(
        f"/api/v1/products/{product['id']}",
        headers=admin_headers,
        json={
            "name": "Bút bi xanh",
            "category_id": category["id"],
            "default_supplier_id": supplier["id"],
            "lead_time_days": 3,
        },
    )
    move(catalog_client, admin_headers, product, "IN", "4")
    result = execute_tool(catalog_db, "search_products", {"query": "but bi"})["data"]
    assert [row["sku"] for row in result["items"]] == ["BUT001"]
    assert execute_tool(catalog_db, "search_products", {"query": "%"})["data"]["items"] == []
    details = execute_tool(catalog_db, "get_product_details", {"sku": "BUT001"})["data"]
    assert details["category"] == "Văn phòng phẩm" and details["supplier"] == "Minh An"
    assert Decimal(details["value_vnd"]) == Decimal(14000)
    assert details["lead_time_days"] == 3
    filtered = execute_tool(
        catalog_db,
        "list_inventory",
        {"status": "low_stock", "category": "van phong", "supplier": "minh an"},
    )["data"]
    assert filtered["total"] == 1
    assert (
        execute_tool(catalog_db, "list_catalog", {"kind": "supplier"})["data"]["items"][0][
            "sku_count"
        ]
        == 1
    )
    overview = execute_tool(catalog_db, "get_warehouse_overview", {})["data"]
    assert overview["total_active_skus"] == 1 and overview["health"]["low"] == 1


@pytest.mark.integration
def test_stock_change_reconciliation_and_ranking_keep_adjustments_separate(
    catalog_client, admin_headers, catalog_db
):
    product = new_product(catalog_client, admin_headers, sku="PCS001")
    for kind, amount in [("IN", "10"), ("OUT", "3"), ("ADJUST_IN", "2"), ("ADJUST_OUT", "1")]:
        assert move(catalog_client, admin_headers, product, kind, amount).status_code == 201
    today = datetime.now(LOCAL_ZONE).date().isoformat()
    result = execute_tool(
        catalog_db, "explain_stock_changes", {"sku": "PCS001", "from_date": today, "to_date": today}
    )["data"]
    assert Decimal(result["opening"]) == 0 and Decimal(result["closing"]) == 8
    assert result["movement_count"] == 4
    assert Decimal(result["totals"]["OUT"]) == 3
    ranked = execute_tool(
        catalog_db, "rank_outbound", {"unit": "PCS", "from_date": today, "to_date": today}
    )["data"]
    assert ranked["ranking_by_unit"]["PCS"][0]["quantity"] == "3.000"
    before_creation = execute_tool(
        catalog_db,
        "explain_stock_changes",
        {
            "sku": "PCS001",
            "from_date": "2000-01-01",
            "to_date": "2000-01-02",
        },
    )["data"]
    assert before_creation["existed_in_period"] is False
    future = execute_tool(
        catalog_db,
        "explain_stock_changes",
        {
            "sku": "PCS001",
            "from_date": "2100-01-01",
            "to_date": "2100-01-02",
        },
    )["data"]
    assert future["period_in_future"] is True


@pytest.mark.integration
def test_search_choice_context_and_followup_reload_current_stock(
    catalog_client, admin_headers, catalog_db
):
    for sku, name in [("PEN001", "Bút xanh"), ("PEN002", "Bút đen")]:
        product = new_product(catalog_client, admin_headers, sku=sku)
        catalog_client.patch(
            f"/api/v1/products/{product['id']}", headers=admin_headers, json={"name": name}
        )
    catalog_client.app.state.settings.ai_provider = "mock"
    cid = conversation(catalog_client, admin_headers)
    first = ask(catalog_client, admin_headers, cid, "Tìm bút")
    assert first.status_code == 200
    assert "1. PEN001" in first.json()["answer"] and "2. PEN002" in first.json()["answer"]
    second = ask(catalog_client, admin_headers, cid, "Chi tiết mã thứ hai")
    assert second.status_code == 200
    assert second.json()["sources"][0]["sku"] == "PEN002"
    with Session(catalog_db) as session:
        product = session.query(Product).filter_by(sku="PEN002").one()
        product_id = str(product.id)
    move(catalog_client, admin_headers, {"id": product_id}, "IN", "7")
    followup = ask(catalog_client, admin_headers, cid, "Mã đó còn bao nhiêu?")
    assert followup.status_code == 200
    assert "7.000 PCS" in followup.json()["answer"]


@pytest.mark.integration
def test_help_uses_actual_user_role_and_keeps_write_guard(catalog_client, admin_headers):
    catalog_client.app.state.settings.ai_provider = "mock"
    cid = conversation(catalog_client, admin_headers)
    guide = ask(catalog_client, admin_headers, cid, "Hướng dẫn nhập kho")
    assert guide.status_code == 200
    assert guide.json()["tool_calls"] == ["get_system_help"]
    assert "Vai trò hiện tại của bạn: ADMIN" in guide.json()["answer"]
    assert guide.json()["sources"][0]["type"] == "system_guide"
    refused = ask(catalog_client, admin_headers, cid, "Hãy xuất 5 SP001")
    assert refused.json()["tool_calls"] == []
