"""Additional read tools for product knowledge and warehouse analysis."""

from decimal import Decimal

from sqlalchemy import exists, func, select

from app.core.dates import date_bounds
from app.db.models import AuditLog, Category, Product, StockBalance, StockMovement, Supplier
from app.modules.ai.knowledge import system_help
from app.modules.ai.schemas import (
    CatalogArgs,
    HelpArgs,
    InventoryArgs,
    PeriodArgs,
    RankingArgs,
    SkuArgs,
    StockChangeArgs,
)
from app.modules.ai.tool_queries import STOCK, contains_text, encode_row, stock_row
from app.modules.reporting.insights import inventory_health, top_outbound
from app.modules.reporting.queries import get_summary


def overview(session, args, now):
    summary = get_summary(session, args.from_date, args.to_date)
    return {
        **{key: value for key, value in summary.items() if key not in {"as_of", "timezone"}},
        "date_from": args.from_date.isoformat(),
        "date_to": args.to_date.isoformat(),
        "health": inventory_health(session),
        "archived_skus": session.scalar(
            select(func.count()).select_from(Product).where(Product.is_active.is_(False))
        ),
        "has_demo_data": session.scalar(
            select(exists(select(AuditLog.id).where(AuditLog.event_type == "DEMO_DATA_IMPORTED")))
        ),
    }


def product_details(session, args, now):
    row = (
        session.execute(
            STOCK.add_columns(
                Product.unit_cost_vnd,
                Category.name.label("category"),
                Supplier.name.label("supplier"),
                Supplier.is_active.label("supplier_active"),
            )
            .outerjoin(Category, Product.category_id == Category.id)
            .outerjoin(Supplier, Product.default_supplier_id == Supplier.id)
            .where(Product.sku == args.sku)
        )
        .mappings()
        .first()
    )
    if not row:
        return {"sku": args.sku, "found": False}
    return {**encode_row(row), "value_vnd": format(row["on_hand"] * row["unit_cost_vnd"], "f")}


def list_inventory(session, args, now):
    query = (
        STOCK.add_columns(
            Product.unit_cost_vnd,
            Category.name.label("category"),
            Supplier.name.label("supplier"),
            (StockBalance.on_hand * Product.unit_cost_vnd).label("value_vnd"),
        )
        .outerjoin(Category, Product.category_id == Category.id)
        .outerjoin(Supplier, Product.default_supplier_id == Supplier.id)
    )
    if args.status == "archived":
        query = query.where(Product.is_active.is_(False))
    elif args.status != "all":
        query = query.where(Product.is_active.is_(True))
    if args.status == "low_stock":
        query = query.where(Product.min_stock > 0, StockBalance.on_hand < Product.min_stock)
    if args.status == "out_of_stock":
        query = query.where(StockBalance.on_hand == 0)
    if args.status == "no_outbound":
        start, end = date_bounds(args.from_date, args.to_date)
        query = query.where(
            ~exists(
                select(StockMovement.id).where(
                    StockMovement.product_id == Product.id,
                    StockMovement.movement_type == "OUT",
                    StockMovement.occurred_at >= start,
                    StockMovement.occurred_at < end,
                )
            )
        )
    if args.unit:
        query = query.where(Product.unit == args.unit)
    if args.category:
        query = query.where(contains_text(Category.name, args.category))
    if args.supplier:
        query = query.where(contains_text(Supplier.name, args.supplier))
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    ordering = {
        "sku": [Product.sku],
        "on_hand_desc": [StockBalance.on_hand.desc(), Product.sku],
        "value_desc": [(StockBalance.on_hand * Product.unit_cost_vnd).desc(), Product.sku],
        "lowest_coverage": [
            (StockBalance.on_hand / func.nullif(Product.min_stock, 0)).asc().nulls_last(),
            Product.sku,
        ],
    }
    rows = session.execute(query.order_by(*ordering[args.sort]).limit(args.limit)).mappings().all()
    return {
        "items": [encode_row(row) for row in rows],
        "total": total,
        "truncated": total > len(rows),
        "status": args.status,
        "unit": args.unit,
        "sort": args.sort,
        "from_date": args.from_date.isoformat(),
        "to_date": args.to_date.isoformat(),
    }


def stock_changes(session, args, now):
    row = stock_row(session, args.sku)
    if not row:
        return {"sku": args.sku, "found": False}
    start, end = date_bounds(args.from_date, args.to_date)
    product_id = session.scalar(select(Product.id).where(Product.sku == args.sku))

    def balance_at(boundary):
        value = session.scalar(
            select(StockMovement.stock_after)
            .where(StockMovement.product_id == product_id, StockMovement.occurred_at < boundary)
            .order_by(StockMovement.occurred_at.desc(), StockMovement.id.desc())
            .limit(1)
        )
        return value if value is not None else Decimal(0)

    opening, closing = balance_at(start), balance_at(end)
    rows = session.execute(
        select(StockMovement.movement_type, func.sum(StockMovement.quantity), func.count())
        .where(
            StockMovement.product_id == product_id,
            StockMovement.occurred_at >= start,
            StockMovement.occurred_at < end,
        )
        .group_by(StockMovement.movement_type)
    ).all()
    totals = {kind: "0" for kind in ["IN", "OUT", "ADJUST_IN", "ADJUST_OUT"]}
    count = 0
    for kind, quantity, amount in rows:
        totals[kind], count = str(quantity), count + amount
    return {
        "sku": args.sku,
        "unit": row["unit"],
        "from_date": args.from_date.isoformat(),
        "to_date": args.to_date.isoformat(),
        "opening": str(opening),
        "closing": str(closing),
        "current_on_hand": str(row["on_hand"]),
        "totals": totals,
        "movement_count": count,
    }


def rank_outbound(session, args, now):
    start, end = date_bounds(args.from_date, args.to_date)
    rows = top_outbound(session, start, end, limit=args.limit)
    groups = {
        unit: [{key: value for key, value in row.items() if key != "product_id"} for row in items]
        for unit, items in rows.items()
        if args.unit is None or unit == args.unit
    }
    return {
        "ranking_by_unit": groups,
        "from_date": args.from_date.isoformat(),
        "to_date": args.to_date.isoformat(),
    }


def list_catalog(session, args, now):
    model = Category if args.kind == "category" else Supplier
    foreign_key = Product.category_id if args.kind == "category" else Product.default_supplier_id
    query = select(model.id, model.name, model.is_active, func.count(Product.id).label("sku_count"))
    query = query.outerjoin(Product, foreign_key == model.id)
    if args.active is not None:
        query = query.where(model.is_active.is_(args.active))
    if args.query:
        query = query.where(contains_text(model.name, args.query))
    rows = (
        session.execute(
            query.group_by(model.id, model.name, model.is_active)
            .order_by(model.name, model.id)
            .limit(args.limit + 1)
        )
        .mappings()
        .all()
    )
    return {
        "kind": args.kind,
        "items": [
            {key: value for key, value in row.items() if key != "id"} for row in rows[: args.limit]
        ],
        "truncated": len(rows) > args.limit,
    }


DETAIL_TOOLS = {
    "get_system_help": (
        HelpArgs,
        system_help,
        "system_guide",
        "Giải thích chức năng, hướng dẫn thao tác và quy tắc. Không thực hiện thao tác ghi.",
    ),
    "get_warehouse_overview": (
        PeriodArgs,
        overview,
        "warehouse_report",
        "Tổng quan toàn kho: SKU, hết hàng, ngưỡng, giá trị VND và giao dịch trong kỳ.",
    ),
    "get_product_details": (
        SkuArgs,
        product_details,
        "products",
        "Thông tin SKU: tồn, ngưỡng, đơn giá, giá trị, danh mục, nhà cung cấp, thời gian chờ.",
    ),
    "list_inventory": (
        InventoryArgs,
        list_inventory,
        "stock_balance",
        "Lọc hàng hết/ẩn/chưa xuất, danh mục/NCC/đơn vị; sort lượng phải chỉ định unit.",
    ),
    "explain_stock_changes": (
        StockChangeArgs,
        stock_changes,
        "stock_movements",
        "Giải thích tồn đầu/cuối kỳ của SKU và đủ bốn loại nhập/xuất/điều chỉnh.",
    ),
    "rank_outbound": (
        RankingArgs,
        rank_outbound,
        "stock_movements",
        "Top SKU xuất nhiều trong kỳ; tách PCS/KG/LITER, chỉ OUT, không tính ADJUST_OUT.",
    ),
    "list_catalog": (
        CatalogArgs,
        list_catalog,
        "catalog",
        "Liệt kê/tìm danh mục hoặc nhà cung cấp cùng trạng thái và số SKU liên kết.",
    ),
}
