from decimal import Decimal


def money(value) -> str:
    whole, fraction = f"{Decimal(value):.2f}".split(".")
    grouped = f"{int(whole):,}".replace(",", ".")
    return grouped + ("," + fraction if int(fraction) else "") + "đ"


def help_answer(data):
    role = (
        f"Vai trò hiện tại của bạn: {data['current_role']}.\n" if data.get("current_role") else ""
    )
    return role + data["title"] + "\n" + "\n".join("• " + section for section in data["sections"])


def overview_answer(data):
    health = data["health"]
    body = (
        f"Kho hiện có {data['total_active_skus']} SKU hoạt động và {data['archived_skus']} SKU ngừng hoạt động.\n"
        f"• Đủ ngưỡng: {health['healthy']}; còn hàng nhưng dưới ngưỡng: {health['low']}; hết hàng: {health['out_of_stock']}.\n"
        f"• Dưới ngưỡng tối thiểu (gồm cả hàng hết khi min_stock > 0): {data['low_stock_count']} SKU.\n"
        f"• Giá trị tồn ước tính hiện tại: {money(data['estimated_inventory_value_vnd'])}, gồm hàng ngừng hoạt động còn tồn.\n"
    )
    body += "\n".join(f"• Tồn {unit}: {qty}." for unit, qty in data["stock_by_unit"].items())
    body += f"\nTừ {data['date_from']} đến hết {data['date_to']}: {data['movement_count']} giao dịch, bao gồm điều chỉnh."
    if health["out_of_stock"]:
        body += (
            "\nƯu tiên kiểm tra hàng hết trước, sau đó xem hàng dưới ngưỡng và gợi ý nhập từng SKU."
        )
    if data["has_demo_data"]:
        body += "\nKho có dữ liệu mô phỏng: SKU DEMO- và giao dịch [DEMO] cần phân biệt với nghiệp vụ thực tế."
    return body


def product_answer(data):
    body = (
        f"{data['sku']} — {data['name']}\n"
        f"• Trạng thái: {'đang hoạt động' if data['is_active'] else 'đã ngừng hoạt động'}.\n"
        f"• Tồn hiện tại: {data['on_hand']} {data['unit']}; ngưỡng tối thiểu: {data['min_stock']} {data['unit']}.\n"
        f"• Đơn giá hiện tại: {money(data['unit_cost_vnd'])}/{data['unit']}; giá trị tồn ước tính: {money(data['value_vnd'])}.\n"
        f"• Danh mục: {data['category'] or 'Chưa phân loại'}.\n"
        f"• Nhà cung cấp mặc định: {data['supplier'] or 'Chưa gán'}; thời gian chờ dự kiến: {data['lead_time_days']} ngày."
    )
    if data["supplier"] and not data["supplier_active"]:
        body += "\nNhà cung cấp mặc định hiện đã ngừng hoạt động."
    return body


def inventory_answer(data):
    labels = {
        "active": "Hàng đang hoạt động",
        "all": "Toàn bộ hàng",
        "low_stock": "Hàng dưới ngưỡng",
        "out_of_stock": "Hàng hết",
        "archived": "Hàng ngừng hoạt động",
        "no_outbound": "Hàng chưa có OUT trong kỳ",
    }
    body = f"{labels[data['status']]}: {data['total']} SKU phù hợp. Tồn hiển thị là hiện tại."
    if data["status"] == "no_outbound":
        body += f" Khoảng ngày {data['from_date']} đến hết {data['to_date']}."
    for index, row in enumerate(data["items"], 1):
        body += (
            f"\n{index}. {row['sku']} — {row['name']}: {row['on_hand']} {row['unit']}"
            f", ngưỡng {row['min_stock']}; giá trị ước tính {money(row['value_vnd'])}."
        )
    if data["truncated"]:
        body += (
            "\nDanh sách đã giới hạn; hãy lọc theo danh mục, nhà cung cấp hoặc đơn vị để xem thêm."
        )
    return body


def changes_answer(data):
    totals = data["totals"]
    body = (
        f"Biến động {data['sku']} từ {data['from_date']} đến hết {data['to_date']} (giờ Việt Nam):\n"
        f"• Tồn đầu kỳ: {data['opening']} {data['unit']}.\n"
        f"• Nhập IN: +{totals['IN']}; xuất OUT: −{totals['OUT']}.\n"
        f"• Điều chỉnh tăng: +{totals['ADJUST_IN']}; điều chỉnh giảm: −{totals['ADJUST_OUT']}.\n"
        f"• Tồn cuối kỳ: {data['closing']} {data['unit']}; {data['movement_count']} giao dịch.\n"
        "Đối soát: đầu kỳ + IN + ADJUST_IN − OUT − ADJUST_OUT = cuối kỳ."
    )
    if not data["movement_count"]:
        body += "\nKhông có giao dịch trong kỳ; không suy ra có xuất hàng."
    if Decimal(data["current_on_hand"]) != Decimal(data["closing"]):
        body += f"\nTồn hiện tại {data['current_on_hand']} {data['unit']} khác cuối kỳ đã chọn."
    return body


def ranking_answer(data):
    body = f"Xếp hạng lượng OUT từ {data['from_date']} đến hết {data['to_date']}:"
    for unit, rows in data["ranking_by_unit"].items():
        body += f"\n{unit}:" + ("" if rows else " Chưa có OUT.")
        for index, row in enumerate(rows, 1):
            body += f"\n{index}. {row['sku']} — {row['name']}: {row['quantity']} {unit}."
    return (
        body
        + "\nXếp hạng riêng từng đơn vị; không cộng khác đơn vị và không tính ADJUST_OUT. Đây là lượng xuất, chưa phải doanh thu."
    )


def catalog_answer(data):
    title = "Danh mục" if data["kind"] == "category" else "Nhà cung cấp"
    if not data["items"]:
        return f"Không tìm thấy {title.lower()} phù hợp."
    body = (
        title
        + ":\n"
        + "\n".join(
            f"• {row['name']}: {'hoạt động' if row['is_active'] else 'ngừng hoạt động'}, {row['sku_count']} SKU liên kết."
            for row in data["items"]
        )
    )
    return body + ("\nDanh sách đã giới hạn; hãy thu hẹp tìm kiếm." if data["truncated"] else "")


DETAIL_RENDERERS = {
    "get_system_help": help_answer,
    "get_warehouse_overview": overview_answer,
    "get_product_details": product_answer,
    "list_inventory": inventory_answer,
    "explain_stock_changes": changes_answer,
    "rank_outbound": ranking_answer,
    "list_catalog": catalog_answer,
}
