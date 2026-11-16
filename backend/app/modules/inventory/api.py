from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from app.core.schemas import Page
from app.db.models import User
from app.db.session import get_session
from app.modules.auth.dependencies import current_user
from app.modules.catalog.schemas import ProductRead
from app.modules.inventory.queries import list_balances, list_movements
from app.modules.inventory.schemas import MovementCreate, MovementRead
from app.modules.inventory.service import post_movement

router = APIRouter(prefix="/stock", tags=["Inventory"], dependencies=[Depends(current_user)])


@router.post("/movements", status_code=201, response_model=MovementRead)
def create_movement(
    payload: MovementCreate,
    response: Response,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    result, duplicate = post_movement(session, user, payload, idempotency_key)
    if duplicate:
        response.status_code = 200
    return result


@router.get("/balances", response_model=Page[ProductRead])
def balances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=255),
    low_stock: bool = False,
    active: bool | None = True,
    category_id: UUID | None = None,
    session: Session = Depends(get_session),
):
    return list_balances(
        session,
        page=page,
        page_size=page_size,
        search=search,
        low_stock=low_stock,
        active=active,
        category_id=category_id,
    )


@router.get("/movements", response_model=Page[MovementRead])
def history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sku: str | None = Query(None, max_length=64),
    movement_type: Literal["IN", "OUT", "ADJUST_IN", "ADJUST_OUT"] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    actor_id: UUID | None = None,
    session: Session = Depends(get_session),
):
    return list_movements(
        session,
        page=page,
        page_size=page_size,
        sku=sku,
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
        actor_id=actor_id,
    )
