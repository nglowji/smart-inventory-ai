import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.db.models import Product, StockBalance, StockMovement, Supplier, User
from app.modules.inventory.schemas import MovementCreate
from app.modules.inventory.serializers import movement_output


def replay(session: Session, existing: StockMovement, fingerprint: str):
    if existing.request_fingerprint != fingerprint:
        raise DomainError(409, "IDEMPOTENCY_CONFLICT", "Mã giao dịch đã dùng cho yêu cầu khác.")
    product = session.get(Product, existing.product_id)
    actor = session.get(User, existing.actor_id)
    return movement_output(existing, product, actor.email), True


def post_movement(session: Session, user: User, payload: MovementCreate, key: UUID):
    if user.role == "VIEWER" or (
        payload.movement_type.startswith("ADJUST") and user.role != "ADMIN"
    ):
        raise DomainError(403, "FORBIDDEN", "Bạn không có quyền tạo loại giao dịch này.")
    data = payload.model_dump(mode="json")
    data["quantity"] = f"{payload.quantity:.3f}"
    data["actor_id"] = str(user.id)
    fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    existing = session.scalar(
        select(StockMovement).where(StockMovement.idempotency_key == str(key))
    )
    if existing:
        return replay(session, existing, fingerprint)

    # Coordinate with catalog changes: product first, then balance. Both locks live in this txn.
    product = session.scalar(
        select(Product).where(Product.id == payload.product_id).with_for_update()
    )
    if product is None:
        raise DomainError(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm.")
    # A retry may have been waiting for this product while the first request committed.
    existing = session.scalar(
        select(StockMovement).where(StockMovement.idempotency_key == str(key))
    )
    if existing:
        return replay(session, existing, fingerprint)
    if not product.is_active:
        raise DomainError(409, "PRODUCT_ARCHIVED", "Sản phẩm đã ngừng hoạt động.")
    if product.unit == "PCS" and payload.quantity != payload.quantity.to_integral_value():
        raise DomainError(422, "INVALID_QUANTITY_UNIT", "Đơn vị PCS chỉ nhận số lượng nguyên.")
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
    delta = payload.quantity if payload.movement_type in ("IN", "ADJUST_IN") else -payload.quantity
    before, after = balance.on_hand, balance.on_hand + delta
    if after < 0:
        raise DomainError(409, "INSUFFICIENT_STOCK", "Tồn kho không đủ để xuất số lượng yêu cầu.")
    if after > Decimal("99999999999.999"):
        raise DomainError(422, "INVALID_QUANTITY", "Tồn kho vượt giới hạn lưu trữ.")
    movement = StockMovement(
        **payload.model_dump(),
        actor_id=user.id,
        stock_before=before,
        stock_after=after,
        idempotency_key=str(key),
        request_fingerprint=fingerprint,
    )
    balance.on_hand = after
    balance.updated_at = datetime.now(UTC)
    session.add(movement)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "")
        if constraint != "uq_stock_movements_idempotency_key":
            raise
        # A concurrent retry won the key; the failed transaction's balance change rolled back.
        existing = session.scalar(
            select(StockMovement).where(StockMovement.idempotency_key == str(key))
        )
        if existing is None:
            raise
        return replay(session, existing, fingerprint)
    session.refresh(movement)
    return movement_output(movement, product, user.email), False
