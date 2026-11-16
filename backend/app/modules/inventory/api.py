from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Product, StockBalance, StockMovement, User
from app.db.session import get_session
from app.modules.auth.api import current_user
from app.modules.catalog.service import paginate, product_output
from app.modules.inventory.schemas import MovementCreate
from app.modules.inventory.service import date_bounds, movement_output, post_movement

router = APIRouter(prefix="/stock", tags=["Inventory"], dependencies=[Depends(current_user)])


@router.post("/movements", status_code=201)
def create_movement(
    payload: MovementCreate, response: Response,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
    user: User = Depends(current_user), session: Session = Depends(get_session),
):
    result, duplicate = post_movement(session, user, payload, idempotency_key)
    if duplicate:
        response.status_code = 200
    return result


@router.get("/balances")
def balances(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=255), low_stock: bool = False,
    active: bool | None = True, category_id: UUID | None = None,
    session: Session = Depends(get_session),
):
    statement = select(Product).join(StockBalance).options(joinedload(Product.balance))
    if active is not None:
        statement = statement.where(Product.is_active == active)
    if low_stock:
        statement = statement.where(Product.is_active.is_(True), Product.min_stock > 0,
                                    StockBalance.on_hand < Product.min_stock)
    if search:
        statement = statement.where(Product.sku.icontains(search.strip(), autoescape=True)
                                    | Product.name.icontains(search.strip(), autoescape=True))
    if category_id:
        statement = statement.where(Product.category_id == category_id)
    result = paginate(session, statement.order_by(Product.sku, Product.id), page, page_size)
    result["items"] = [product_output(product) for product in result["items"]]
    return result


@router.get("/movements")
def history(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    sku: str | None = Query(None, max_length=64),
    movement_type: Literal["IN", "OUT", "ADJUST_IN", "ADJUST_OUT"] | None = None,
    date_from: date | None = None, date_to: date | None = None,
    actor_id: UUID | None = None, session: Session = Depends(get_session),
):
    statement = select(StockMovement, Product, User.email).join(
        Product, StockMovement.product_id == Product.id
    ).join(User, StockMovement.actor_id == User.id)
    if sku:
        statement = statement.where(Product.sku == sku.strip().upper())
    if movement_type:
        statement = statement.where(StockMovement.movement_type == movement_type)
    if actor_id:
        statement = statement.where(StockMovement.actor_id == actor_id)
    if date_from or date_to:
        start, end = date_bounds(date_from or date_to, date_to or date_from)
        statement = statement.where(StockMovement.occurred_at >= start,
                                    StockMovement.occurred_at < end)
    total = session.scalar(select(func.count()).select_from(statement.subquery()))
    rows = session.execute(statement.order_by(StockMovement.occurred_at.desc(),
                           StockMovement.id.desc()).offset((page - 1) * page_size).limit(page_size))
    return {"items": [movement_output(*row) for row in rows],
            "total": total, "page": page, "page_size": page_size}
