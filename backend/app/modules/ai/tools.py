"""Bounded read-only tools. No user-supplied SQL, identities or write functions."""

import json
from datetime import timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.dates import date_bounds
from app.core.errors import DomainError
from app.db.models import Product, StockBalance, StockMovement
from app.modules.ai.detail_tools import DETAIL_TOOLS
from app.modules.ai.tool_queries import STOCK, contains_text, encode_row, stock_row
from app.modules.ai.policies import replenishment
from app.modules.ai.schemas import (
    LimitArgs,
    OutboundArgs,
    RecentArgs,
    ReplenishmentArgs,
    SearchArgs,
    SkuArgs,
)

def get_stock(session, args, now):
    row = stock_row(session, args.sku)
    return encode_row(row) if row else {"sku": args.sku, "found": False}


def search(session, args, now):
    rows = (
        session.execute(
            STOCK.where(
                contains_text(Product.sku, args.query) | contains_text(Product.name, args.query)
            )
            .order_by(Product.sku)
            .limit(args.limit + 1)
        )
        .mappings()
        .all()
    )
    return {
        "items": [encode_row(row) for row in rows[: args.limit]],
        "truncated": len(rows) > args.limit,
        "query": args.query,
    }


def low_stock(session, args, now):
    rows = (
        session.execute(
            STOCK.where(
                Product.is_active.is_(True),
                Product.min_stock > 0,
                StockBalance.on_hand < Product.min_stock,
            )
            .order_by(Product.sku)
            .limit(args.limit + 1)
        )
        .mappings()
        .all()
    )
    return {
        "items": [
            {**encode_row(row), "shortage_to_min": str(row["min_stock"] - row["on_hand"])}
            for row in rows[: args.limit]
        ],
        "truncated": len(rows) > args.limit,
    }


def outbound(session, args, now):
    start, end = date_bounds(args.from_date, args.to_date)
    filters = [
        StockMovement.movement_type == "OUT",
        StockMovement.occurred_at >= start,
        StockMovement.occurred_at < end,
    ]
    if args.sku:
        filters.append(Product.sku == args.sku)
    rows = (
        session.execute(
            select(Product.sku, Product.unit, func.sum(StockMovement.quantity).label("outbound"))
            .join(StockMovement, StockMovement.product_id == Product.id)
            .where(*filters)
            .group_by(Product.sku, Product.unit)
            .order_by(Product.sku)
            .limit(21)
        )
        .mappings()
        .all()
    )
    totals = session.execute(
        select(Product.unit, func.sum(StockMovement.quantity))
        .join(StockMovement, StockMovement.product_id == Product.id)
        .where(*filters)
        .group_by(Product.unit)
        .order_by(Product.unit)
    ).all()
    return {
        "from_date": args.from_date.isoformat(),
        "to_date": args.to_date.isoformat(),
        "items": [encode_row(row) for row in rows[:20]],
        "truncated": len(rows) > 20,
        "totals_by_unit": {unit: str(qty) for unit, qty in totals},
        "sku": args.sku,
    }


def recent(session, args, now):
    query = select(
        Product.sku,
        Product.unit,
        StockMovement.movement_type,
        StockMovement.quantity,
        StockMovement.occurred_at,
    )
    query = query.join(StockMovement, StockMovement.product_id == Product.id)
    if args.sku:
        query = query.where(Product.sku == args.sku.upper())
    rows = (
        session.execute(
            query.order_by(StockMovement.occurred_at.desc(), StockMovement.id.desc()).limit(
                args.limit
            )
        )
        .mappings()
        .all()
    )
    return {"items": [encode_row(row) for row in rows]}


def recommend(session, args, now):
    row = stock_row(session, args.sku)
    if not row:
        return {"sku": args.sku, "found": False}
    if not row["is_active"]:
        return {**encode_row(row), "archived": True}
    start = now - timedelta(days=args.lookback_days)
    quantity, count = session.execute(
        select(func.coalesce(func.sum(StockMovement.quantity), 0), func.count())
        .join(Product, StockMovement.product_id == Product.id)
        .where(
            Product.sku == args.sku,
            StockMovement.movement_type == "OUT",
            StockMovement.occurred_at >= start,
            StockMovement.occurred_at <= now,
        )
    ).one()
    return {
        **encode_row(row),
        **replenishment(
            on_hand=row["on_hand"],
            min_stock=row["min_stock"],
            outbound=quantity,
            movement_count=count,
            lead_time_days=row["lead_time_days"],
            lookback_days=args.lookback_days,
            unit=row["unit"],
        ),
        "period_start": start.isoformat(),
        "period_end": now.isoformat(),
    }


REGISTRY = {
    **DETAIL_TOOLS,
    "get_stock_by_sku": (
        SkuArgs,
        get_stock,
        "stock_balance",
        "Tra cứu tồn hiện tại theo SKU chính xác.",
    ),
    "search_products": (
        SearchArgs,
        search,
        "products",
        "Tìm SKU theo tên; hỏi người dùng chọn khi mơ hồ.",
    ),
    "list_low_stock": (
        LimitArgs,
        low_stock,
        "stock_balance",
        "Liệt kê hàng hoạt động dưới ngưỡng tối thiểu.",
    ),
    "summarize_outbound": (
        OutboundArgs,
        outbound,
        "stock_movements",
        "Tổng OUT theo ngày Việt Nam, tách đơn vị; không gồm ADJUST_OUT.",
    ),
    "get_recent_movements": (
        RecentArgs,
        recent,
        "stock_movements",
        "Lịch sử kho gần đây; chỉ đọc, không ghi giao dịch.",
    ),
    "recommend_replenishment": (
        ReplenishmentArgs,
        recommend,
        "replenishment",
        "Gợi ý nhập hàng theo công thức backend, mặc định 30 ngày.",
    ),
}


def definitions():
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": schema.model_json_schema(),
                "strict": False,
            },
        }
        for name, (schema, _, _, description) in REGISTRY.items()
    ]


def execute_tool(engine, name: str, arguments: dict, *, timeout_seconds: float = 10) -> dict:
    if name not in REGISTRY:
        raise DomainError(503, "AI_RESPONSE_INVALID", "Model đề xuất công cụ không hợp lệ.")
    schema, handler, source_type, _ = REGISTRY[name]
    args = schema.model_validate(arguments)
    with Session(engine) as session, session.begin():
        # This database transaction cannot write inventory, even if a handler has a bug.
        session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        session.execute(
            select(
                func.set_config(
                    "statement_timeout",
                    str(max(1, min(3000, int(timeout_seconds * 1000 / 3)))),
                    True,
                )
            )
        )
        now = session.scalar(select(func.statement_timestamp()))
        result = {
            "tool": name,
            "data": handler(session, args, now),
            "source": {
                "type": source_type,
                "sku": getattr(args, "sku", None),
                "as_of": now.isoformat(),
            },
        }
    if len(json.dumps(result, ensure_ascii=False).encode()) > 20_000:
        raise DomainError(
            503, "AI_RESPONSE_INVALID", "Dữ liệu vượt giới hạn trả lời. Hãy hỏi cụ thể hơn."
        )
    return result
