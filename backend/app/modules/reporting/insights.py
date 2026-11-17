"""Bounded dashboard aggregates from one read-only, repeatable snapshot."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, String, case, cast, exists, func, select, text
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Category, Product, StockBalance, StockMovement
from app.modules.reporting.queries import period


def inventory_health(session: Session):
    empty = StockBalance.on_hand == 0
    low = (
        (StockBalance.on_hand > 0)
        & (Product.min_stock > 0)
        & (StockBalance.on_hand < Product.min_stock)
    )
    state = case((empty, "out_of_stock"), (low, "low"), else_="healthy")
    rows = session.execute(
        select(state.label("state"), func.count())
        .select_from(Product)
        .join(StockBalance)
        .where(Product.is_active.is_(True))
        .group_by(state)
    ).all()
    result = {"healthy": 0, "low": 0, "out_of_stock": 0}
    result.update(dict(rows))
    return result


def category_values(session: Session):
    value = func.coalesce(func.sum(StockBalance.on_hand * Product.unit_cost_vnd), 0)
    grouped = (
        select(
            Category.id.label("category_id"),
            func.coalesce(Category.name, "Chưa phân loại").label("name"),
            value.label("value"),
            func.count().label("sku_count"),
        )
        .select_from(Product)
        .join(StockBalance)
        .outerjoin(Category, Product.category_id == Category.id)
        .group_by(Category.id, Category.name)
        .cte("category_values")
    )
    ranked = select(
        grouped,
        func.row_number()
        .over(order_by=(grouped.c.value.desc(), grouped.c.name, grouped.c.category_id))
        .label("rank"),
    ).cte("category_ranked")
    # Six named categories and one remainder retain all value in a bounded chart.
    key = case(
        (ranked.c.rank <= 6, func.coalesce(cast(ranked.c.category_id, String), "uncategorized")),
        else_="other",
    )
    name = case((ranked.c.rank <= 6, ranked.c.name), else_="Các danh mục khác")
    rows = (
        session.execute(
            select(
                key.label("key"),
                name.label("name"),
                func.sum(ranked.c.value).label("value"),
                func.sum(ranked.c.sku_count).label("sku_count"),
            )
            .select_from(ranked)
            .group_by(key, name)
            .order_by(func.min(ranked.c.rank))
        )
        .mappings()
        .all()
    )
    return [
        {
            "key": row["key"],
            "name": row["name"],
            "value_vnd": format(row["value"], "f"),
            "sku_count": row["sku_count"],
        }
        for row in rows
    ]


def movement_activity(session: Session, start, end):
    local_day = cast(func.timezone("Asia/Ho_Chi_Minh", StockMovement.occurred_at), Date)
    rows = session.execute(
        select(local_day.label("day"), StockMovement.movement_type, func.count().label("count"))
        .where(StockMovement.occurred_at >= start, StockMovement.occurred_at < end)
        .group_by(local_day, StockMovement.movement_type)
        .order_by(local_day)
    ).all()
    counts = {kind: 0 for kind in ["IN", "OUT", "ADJUST_IN", "ADJUST_OUT"]}
    days = {}
    for day, kind, count in rows:
        counts[kind] += count
        days[day] = days.get(day, 0) + count
    return (
        [{"movement_type": kind, "count": count} for kind, count in counts.items()],
        [{"date": day, "count": count} for day, count in sorted(days.items())],
    )


def top_outbound(session: Session, start, end):
    totals = (
        select(
            Product.id.label("product_id"),
            Product.sku,
            Product.name,
            Product.unit,
            func.sum(StockMovement.quantity).label("quantity"),
        )
        .join(StockMovement, StockMovement.product_id == Product.id)
        .where(
            StockMovement.movement_type == "OUT",
            StockMovement.occurred_at >= start,
            StockMovement.occurred_at < end,
        )
        .group_by(Product.id, Product.sku, Product.name, Product.unit)
        .cte("outbound_totals")
    )
    ranked = select(
        totals,
        func.row_number()
        .over(partition_by=totals.c.unit, order_by=(totals.c.quantity.desc(), totals.c.sku))
        .label("rank"),
    ).cte("outbound_ranked")
    rows = (
        session.execute(
            select(ranked).where(ranked.c.rank <= 5).order_by(ranked.c.unit, ranked.c.rank)
        )
        .mappings()
        .all()
    )
    result = {unit: [] for unit in ["PCS", "KG", "LITER"]}
    for row in rows:
        result[row["unit"]].append(
            {
                "product_id": row["product_id"],
                "sku": row["sku"],
                "name": row["name"],
                "unit": row["unit"],
                "quantity": f"{row['quantity']:.3f}",
            }
        )
    return result


def get_insights(session: Session, date_from: date | None = None, date_to: date | None = None):
    start_day, end_day, start, end = period(date_from, date_to)
    with Session(session.get_bind()) as snapshot, snapshot.begin():
        snapshot.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        snapshot.execute(text("SET LOCAL statement_timeout = 5000"))
        now = snapshot.scalar(select(func.transaction_timestamp()))
        health = inventory_health(snapshot)
        categories = category_values(snapshot)
        types, daily = movement_activity(snapshot, start, end)
        outbound = top_outbound(snapshot, start, end)
        has_outbound = exists(
            select(StockMovement.id).where(
                StockMovement.product_id == Product.id,
                StockMovement.movement_type == "OUT",
                StockMovement.occurred_at >= start,
                StockMovement.occurred_at < end,
            )
        )
        inactive, no_outbound, demo = snapshot.execute(
            select(
                select(func.count())
                .select_from(Product)
                .where(Product.is_active.is_(False))
                .scalar_subquery(),
                select(func.count())
                .select_from(Product)
                .where(Product.is_active.is_(True), ~has_outbound)
                .scalar_subquery(),
                exists(select(AuditLog.id).where(AuditLog.event_type == "DEMO_DATA_IMPORTED")),
            )
        ).one()
        value = sum((Decimal(row["value_vnd"]) for row in categories), Decimal(0))
    return {
        "health": health,
        "archived_skus": inactive,
        "without_outbound_skus": no_outbound,
        "category_values": categories,
        "estimated_inventory_value_vnd": f"{value:.2f}",
        "movement_types": types,
        "daily_activity": daily,
        "top_outbound": outbound,
        "date_from": start_day,
        "date_to": end_day,
        "as_of": now,
        "timezone": "Asia/Ho_Chi_Minh",
        "has_demo_data": demo,
    }
