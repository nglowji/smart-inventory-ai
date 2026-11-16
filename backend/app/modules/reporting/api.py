from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.orm import Session

from app.db.models import Product, StockBalance, StockMovement
from app.db.session import get_session
from app.modules.auth.api import current_user
from app.modules.inventory.service import LOCAL_ZONE, date_bounds

router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(current_user)])


def period(date_from: date | None, date_to: date | None):
    end = date_to or datetime.now(LOCAL_ZONE).date()
    start = date_from or end - timedelta(days=29)
    return start, end, *date_bounds(start, end)


@router.get("/summary")
def summary(date_from: date | None = None, date_to: date | None = None,
            session: Session = Depends(get_session)):
    start_day, end_day, start, end = period(date_from, date_to)
    # One SQL statement: the KPI set reflects a single PostgreSQL statement snapshot.
    active_count = select(func.count()).select_from(Product).where(Product.is_active.is_(True))
    low_count = select(func.count()).select_from(Product).join(StockBalance).where(
        Product.is_active.is_(True), Product.min_stock > 0, StockBalance.on_hand < Product.min_stock
    )
    value = select(func.coalesce(func.sum(StockBalance.on_hand * Product.unit_cost_vnd), 0)).select_from(StockBalance).join(
        Product, StockBalance.product_id == Product.id
    )
    movements = select(func.count()).select_from(StockMovement).where(
        StockMovement.occurred_at >= start, StockMovement.occurred_at < end
    )
    row = session.execute(select(active_count.scalar_subquery(), low_count.scalar_subquery(),
                                 value.scalar_subquery(), movements.scalar_subquery())).one()
    return {
        "total_active_skus": row[0], "low_stock_count": row[1],
        "estimated_inventory_value_vnd": f"{row[2]:.2f}", "movement_count": row[3],
        "date_from": start_day, "date_to": end_day, "timezone": "Asia/Ho_Chi_Minh",
        "as_of": datetime.now(UTC),
    }


@router.get("/flow")
def flow(date_from: date | None = None, date_to: date | None = None,
         session: Session = Depends(get_session)):
    start_day, end_day, start, end = period(date_from, date_to)
    local_day = cast(func.timezone("Asia/Ho_Chi_Minh", StockMovement.occurred_at), Date)
    rows = session.execute(select(
        local_day.label("day"), Product.unit,
        func.sum(case((StockMovement.movement_type == "IN", StockMovement.quantity),
                      else_=Decimal(0))).label("inbound"),
        func.sum(case((StockMovement.movement_type == "OUT", StockMovement.quantity),
                      else_=Decimal(0))).label("outbound"),
    ).join(Product, StockMovement.product_id == Product.id).where(
        StockMovement.occurred_at >= start, StockMovement.occurred_at < end,
        StockMovement.movement_type.in_(["IN", "OUT"]),
    ).group_by(local_day, Product.unit).order_by(local_day, Product.unit)).all()
    totals = {unit: {"inbound": Decimal(0), "outbound": Decimal(0)}
              for unit in ("PCS", "KG", "LITER")}
    for row in rows:
        totals[row.unit]["inbound"] += row.inbound
        totals[row.unit]["outbound"] += row.outbound
    return {"items": [{"date": row.day, "unit": row.unit, "inbound": f"{row.inbound:.3f}",
                       "outbound": f"{row.outbound:.3f}"} for row in rows],
            "date_from": start_day, "date_to": end_day, "timezone": "Asia/Ho_Chi_Minh",
            "totals": {unit: {key: f"{value:.3f}" for key, value in values.items()}
                       for unit, values in totals.items()},
            "as_of": datetime.now(UTC)}
