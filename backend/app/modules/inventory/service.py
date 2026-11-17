from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.db.models import Product, StockBalance, StockMovement, Supplier, User
from app.modules.audit.service import record_event
from app.modules.inventory.idempotency import request_fingerprint
from app.modules.inventory.policies import (
    require_movement_permission,
    stock_after,
    validate_quantity,
)
from app.modules.inventory.queries import find_movement_by_key
from app.modules.inventory.schemas import MovementCreate
from app.modules.inventory.serializers import movement_output


def replay(session: Session, existing: StockMovement, fingerprint: str):
    if existing.request_fingerprint != fingerprint:
        raise DomainError(409, "IDEMPOTENCY_CONFLICT", "Mã giao dịch đã dùng cho yêu cầu khác.")
    product = session.get(Product, existing.product_id)
    actor = session.get(User, existing.actor_id)
    return movement_output(existing, product, actor.email), True


def post_movement(session: Session, user: User, payload: MovementCreate, key: UUID):
    require_movement_permission(user.role, payload.movement_type)
    fingerprint = request_fingerprint(payload, user.id)
    existing = find_movement_by_key(session, key)
    if existing:
        return replay(session, existing, fingerprint)

    # Coordinate with catalog changes: product first, then balance. Both locks live in this txn.
    product = session.scalar(
        select(Product).where(Product.id == payload.product_id).with_for_update()
    )
    if product is None:
        raise DomainError(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm.")
    # A retry may have been waiting for this product while the first request committed.
    existing = find_movement_by_key(session, key)
    if existing:
        return replay(session, existing, fingerprint)
    if not product.is_active:
        raise DomainError(409, "PRODUCT_ARCHIVED", "Sản phẩm đã ngừng hoạt động.")
    validate_quantity(payload.quantity, product.unit)
    if payload.supplier_id:
        supplier = session.get(Supplier, payload.supplier_id)
        if supplier is None or not supplier.is_active:
            raise DomainError(422, "VALIDATION_ERROR", "Nhà cung cấp không khả dụng.")
    balance = session.scalar(
        select(StockBalance).where(StockBalance.product_id == product.id).with_for_update()
    )
    if balance is None:
        raise DomainError(
            409, "BALANCE_MISSING", "Sản phẩm thiếu dòng tồn kho, cần kiểm tra dữ liệu."
        )
    before = balance.on_hand
    after = stock_after(before, payload.quantity, payload.movement_type)
    movement = StockMovement(
        **payload.model_dump(),
        id=uuid4(),
        actor_id=user.id,
        stock_before=before,
        stock_after=after,
        idempotency_key=str(key),
        request_fingerprint=fingerprint,
    )
    balance.on_hand = after
    balance.updated_at = datetime.now(UTC)
    session.add(movement)
    if payload.movement_type.startswith("ADJUST"):
        record_event(
            session,
            "STOCK_ADJUSTED",
            actor_id=user.id,
            target_type="stock_movement",
            target_id=movement.id,
            details={
                "product_id": str(product.id),
                "movement_type": payload.movement_type,
                "quantity": f"{payload.quantity:.3f}",
            },
        )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "")
        if constraint != "uq_stock_movements_idempotency_key":
            raise
        # A concurrent retry won the key; the failed transaction's balance change rolled back.
        existing = find_movement_by_key(session, key)
        if existing is None:
            raise
        return replay(session, existing, fingerprint)
    session.refresh(movement)
    return movement_output(movement, product, user.email), False
