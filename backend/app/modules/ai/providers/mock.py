import json
import re
from datetime import datetime, timedelta

from app.core.dates import LOCAL_ZONE
from app.modules.ai.policies import fold_text, requests_write
from app.modules.ai.providers.base import ToolCall


class MockProvider:
    """Explicit offline test mode; all quantities still come from database tools."""

    def plan(self, history: list[dict], question: str) -> list[ToolCall]:
        normalized = fold_text(question)
        if requests_write(question):
            return []
        sku_match = re.search(r"\b[A-Z][A-Z0-9_-]*\d[A-Z0-9_-]*\b", question.upper())
        sku = sku_match.group() if sku_match else None
        if not sku and any(term in normalized for term in ["ma do", "ma thu hai", "con bao nhieu"]):
            for item in reversed(history):
                try:
                    memory = json.loads(item["content"]).get("verified_context", {})
                    choices = memory.get("choices", [])
                    sku = (
                        choices[1]
                        if "ma thu hai" in normalized and len(choices) > 1
                        else memory.get("sku")
                    )
                    if sku:
                        break
                except (ValueError, TypeError, AttributeError):
                    continue
        if any(term in normalized for term in ["huong dan", "quy trinh", "quyen", "vai tro"]):
            topic = "roles" if "quyen" in normalized or "vai tro" in normalized else "inventory"
            return [ToolCall("get_system_help", {"topic": topic})]
        if "tong quan kho" in normalized:
            return [ToolCall("get_warehouse_overview", {})]
        if sku and any(
            term in normalized for term in ["chi tiet", "nha cung cap", "danh muc", "gia bao nhieu"]
        ):
            return [ToolCall("get_product_details", {"sku": sku})]
        if "sap het" in normalized or "duoi nguong" in normalized or "low stock" in normalized:
            return [ToolCall("list_low_stock", {})]
        if sku and any(term in normalized for term in ("goi y", "nen nhap", "de xuat")):
            return [ToolCall("recommend_replenishment", {"sku": sku})]
        if "tong xuat" in normalized or "da xuat" in normalized:
            today = datetime.now(LOCAL_ZONE).date()
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", question)
            start = dates[0] if dates else today.isoformat()
            end = dates[1] if len(dates) > 1 else start
            if "30 ngay" in normalized and not dates:
                start = (today - timedelta(days=29)).isoformat()
            return [
                ToolCall(
                    "summarize_outbound",
                    {"from_date": start, "to_date": end, **({"sku": sku} if sku else {})},
                )
            ]
        if "lich su" in normalized or "gan day" in normalized:
            return [ToolCall("get_recent_movements", {"sku": sku} if sku else {})]
        if sku:
            return [ToolCall("get_stock_by_sku", {"sku": sku})]
        match = re.search(
            r"(?:tìm|tim)\s+(?:sản phẩm\s+|san pham\s+)?(.+)", question, re.IGNORECASE
        )
        return [ToolCall("search_products", {"query": match[1][:100]})] if match else []
