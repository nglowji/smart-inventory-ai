from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.dates import date_bounds
from app.db.models import Product, StockBalance, StockMovement, User
from app.db.pagination import paginate
from app.modules.catalog.serializers import product_output
from app.modules.inventory.serializers import movement_output


def list_balances(
    session: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    low_stock: bool = False,
    active: bool | None = True,
    category_id: UUID | None = None,
):
    statement = select(Product).join(StockBalance).options(joinedload(Product.balance))
    if active is not None:
        statement = statement.where(Product.is_active == active)
    if low_stock:
        statement = statement.where(
            Product.is_active.is_(True),
            Product.min_stock > 0,
            StockBalance.on_hand < Product.min_stock,
        )
    if search:
        statement = statement.where(
            Product.sku.icontains(search.strip(), autoescape=True)
            | Product.name.icontains(search.strip(), autoescape=True)
        )
    if category_id:
        statement = statement.where(Product.category_id == category_id)
    result = paginate(session, statement.order_by(Product.sku, Product.id), page, page_size)
    result["items"] = [product_output(product) for product in result["items"]]
    return result


def list_movements(
    session: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    sku: str | None = None,
    movement_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    actor_id: UUID | None = None,
):
    statement = (
        select(StockMovement, Product, User.email)
        .join(Product, StockMovement.product_id == Product.id)
        .join(User, StockMovement.actor_id == User.id)
    )
    if sku:
        statement = statement.where(Product.sku == sku.strip().upper())
    if movement_type:
        statement = statement.where(StockMovement.movement_type == movement_type)
    if actor_id:
        statement = statement.where(StockMovement.actor_id == actor_id)
    if date_from or date_to:
        start, end = date_bounds(date_from or date_to, date_to or date_from)
        statement = statement.where(
            StockMovement.occurred_at >= start, StockMovement.occurred_at < end
        )
    total = session.scalar(select(func.count()).select_from(statement.subquery()))
    rows = session.execute(
        statement.order_by(StockMovement.occurred_at.desc(), StockMovement.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [movement_output(*row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
