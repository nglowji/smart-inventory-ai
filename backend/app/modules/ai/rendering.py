"""Grounded Vietnamese answers. Free-form model output never becomes numeric evidence."""

from datetime import datetime

from app.core.dates import LOCAL_ZONE
from app.modules.ai.detail_rendering import DETAIL_RENDERERS

READ_ONLY_ANSWER = (
    "Trợ lý chỉ tra cứu dữ liệu kho và gợi ý nhập hàng. "
    "Để nhập, xuất hoặc điều chỉnh tồn, hãy dùng màn hình Giao dịch kho với tài khoản có quyền."
)
CLARIFY_ANSWER = (
    "Bạn muốn tra cứu SKU nào? Mình có thể tìm sản phẩm theo tên, xem tồn, "
    "hàng dưới ngưỡng, tổng xuất theo ngày, lịch sử và gợi ý nhập hàng."
)


def render_result(result: dict) -> str:
    name, data = result["tool"], result["data"]
    if data.get("found") is False:
        body = f"Không tìm thấy SKU {data['sku']} trong dữ liệu kho. Bạn hãy kiểm tra lại mã."
    elif name in DETAIL_RENDERERS:
        body = DETAIL_RENDERERS[name](data)
    elif name == "get_stock_by_sku":
        body = (
            f"{data['sku']} — {data['name']}: còn {data['on_hand']} {data['unit']}; "
            f"ngưỡng tối thiểu {data['min_stock']} {data['unit']}."
        )
        if not data["is_active"]:
            body += " Sản phẩm đã ngừng hoạt động."
    elif name in {"search_products", "list_low_stock"}:
        if not data["items"]:
            body = (
                "Không có sản phẩm phù hợp."
                if name == "search_products"
                else "Không có sản phẩm hoạt động dưới ngưỡng tối thiểu."
            )
        else:
            body = "\n".join(
                (f"{index}. " if name == "search_products" else "• ")
                + f"{row['sku']} — {row['name']}: còn {row['on_hand']} {row['unit']}"
                + (
                    f", thiếu {row['shortage_to_min']} {row['unit']} so với ngưỡng."
                    if name == "list_low_stock"
                    else "."
                )
                for index, row in enumerate(data["items"], 1)
            )
            if name == "search_products":
                body += "\nBạn muốn tra cứu mã SKU nào trong danh sách? Có thể chọn theo số thứ tự."
            if data["truncated"]:
                body += "\nDanh sách đã giới hạn; còn kết quả khác. Hãy thu hẹp câu hỏi."
    elif name == "summarize_outbound":
        body = f"Xuất hàng từ {data['from_date']} đến hết {data['to_date']} (giờ Việt Nam):"
        body += "\n" + (
            "\n".join(f"• Tổng {qty} {unit}." for unit, qty in data["totals_by_unit"].items())
            or "Không có giao dịch OUT trong khoảng ngày này."
        )
        body += "\n" + "\n".join(
            f"• {row['sku']}: {row['outbound']} {row['unit']}." for row in data["items"]
        )
        if data["truncated"]:
            body += "\nChỉ hiển thị 20 SKU; tổng theo đơn vị bao gồm toàn bộ kết quả."
        body += "\nKhông tính điều chỉnh giảm tồn (ADJUST_OUT) vào lượng xuất."
    elif name == "get_recent_movements":
        body = (
            "\n".join(
                f"• {row['sku']}: {row['movement_type']} {row['quantity']} {row['unit']} — "
                + datetime.fromisoformat(row["occurred_at"])
                .astimezone(LOCAL_ZONE)
                .strftime("%H:%M %d/%m/%Y")
                for row in data["items"]
            )
            or "Chưa có giao dịch phù hợp."
        )
    elif data.get("archived"):
        body = f"SKU {data['sku']} đã ngừng hoạt động; không đề xuất nhập hàng."
    else:
        body = (
            f"{data['sku']}: gợi ý nhập {data['suggested_qty']} {data['unit']}; "
            f"hiện còn {data['on_hand']} {data['unit']}."
        )
        if data["insufficient_history"]:
            body += (
                "\nChưa có lịch sử OUT trong kỳ nên chưa đủ dữ liệu ước lượng tiêu thụ. "
                "Chỉ gợi ý bù đến ngưỡng tối thiểu."
            )
        else:
            body += (
                f"\nTrong {data['lookback_days']} ngày "
                f"đã xuất {data['outbound_qty_period']} {data['unit']}; "
                f"thời gian chờ {data['lead_time_days']} ngày; "
                f"ngưỡng an toàn {data['min_stock']} {data['unit']}."
                "\nMục tiêu = (lượng xuất / số ngày) × thời gian chờ + ngưỡng an toàn "
                f"= {data['target_stock']} {data['unit']}. "
                "Lượng nhập được làm tròn lên theo đơn vị."
            )
        body += f"\n{data['assumptions']} Đây là gợi ý hỗ trợ quyết định."
    as_of = datetime.fromisoformat(result["source"]["as_of"]).astimezone(LOCAL_ZONE)
    source = "hướng dẫn nghiệp vụ SmartInventory AI" if name == "get_system_help" else "dữ liệu kho"
    return (
        body.strip() + f"\nNguồn: {source}, đối chiếu lúc {as_of:%H:%M:%S %d/%m/%Y} (giờ Việt Nam)."
    )
