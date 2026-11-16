"""Inventory rules independent of HTTP and database sessions."""

from decimal import Decimal

from app.core.errors import DomainError

MAX_STOCK = Decimal("99999999999.999")
INBOUND_TYPES = frozenset({"IN", "ADJUST_IN"})
OUTBOUND_TYPES = frozenset({"OUT", "ADJUST_OUT"})


def require_movement_permission(role: str, movement_type: str) -> None:
    if role not in {"ADMIN", "STAFF"} or (movement_type.startswith("ADJUST") and role != "ADMIN"):
        raise DomainError(403, "FORBIDDEN", "Bạn không có quyền tạo loại giao dịch này.")


def validate_quantity(quantity: Decimal, unit: str) -> None:
    if (
        not quantity.is_finite()
        or quantity <= 0
        or quantity > MAX_STOCK
        or quantity != quantity.quantize(Decimal("0.001"))
    ):
        raise DomainError(422, "INVALID_QUANTITY", "Số lượng phải dương, tối đa 3 số thập phân.")
    if unit == "PCS" and quantity != quantity.to_integral_value():
        raise DomainError(422, "INVALID_QUANTITY_UNIT", "Đơn vị PCS chỉ nhận số lượng nguyên.")


def stock_after(on_hand: Decimal, quantity: Decimal, movement_type: str) -> Decimal:
    if movement_type not in INBOUND_TYPES | OUTBOUND_TYPES:
        raise DomainError(422, "VALIDATION_ERROR", "Loại giao dịch không hợp lệ.")
    after = on_hand + (quantity if movement_type in INBOUND_TYPES else -quantity)
    if after < 0:
        raise DomainError(409, "INSUFFICIENT_STOCK", "Tồn kho không đủ để xuất số lượng yêu cầu.")
    if after > MAX_STOCK:
        raise DomainError(422, "INVALID_QUANTITY", "Tồn kho vượt giới hạn lưu trữ.")
    return after
