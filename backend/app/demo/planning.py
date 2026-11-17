from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from app.demo.dataset import PRODUCTS, ProductSpec
from app.modules.inventory.policies import stock_after, validate_quantity


@dataclass(frozen=True)
class PlannedMovement:
    movement_type: str
    quantity: Decimal
    occurred_at: datetime
    reason: str
    before: Decimal
    after: Decimal


def plan_product(spec: ProductSpec, index: int, anchor: datetime) -> list[PlannedMovement]:
    if spec.state == "no_history":
        return []
    start = anchor - timedelta(days=83) + timedelta(minutes=index * 2)
    batch = Decimal(spec.batch)
    raw = []
    for cycle in range(12):
        day = start + timedelta(days=cycle * 7)
        raw.append((day, "IN", batch * (2 + (index + cycle) % 3), "Nhập bổ sung theo đợt"))
        for offset, multiplier in [
            (2, 2 + (index + cycle) % 2),
            (4, 1 + (index + 2 * cycle) % 3),
            (6, 2),
        ]:
            raw.append(
                (
                    day + timedelta(days=offset),
                    "OUT",
                    batch * multiplier,
                    [
                        "Cấp hàng cho bộ phận vận hành",
                        "Giao đơn hàng định kỳ",
                        "Cấp vật tư theo yêu cầu",
                    ][offset // 2 - 1],
                )
            )
    # Every cycle consumes more than it receives. This opening stock keeps all prefixes valid.
    opening = spec.target + sum(qty if kind == "OUT" else -qty for _, kind, qty, _ in raw)
    raw.append((start - timedelta(minutes=30), "IN", opening, "Nhập số dư đầu kỳ mô phỏng"))
    if index % 9 == 1:
        day = start + timedelta(days=40)
        raw.extend(
            [
                (day + timedelta(minutes=10), "ADJUST_IN", batch, "Kiểm kê phát hiện hàng bổ sung"),
                (day + timedelta(minutes=20), "ADJUST_OUT", batch, "Kiểm kê xác nhận hàng hư hỏng"),
            ]
        )
    balance, result = Decimal(0), []
    for occurred_at, kind, quantity, reason in sorted(raw):
        validate_quantity(quantity, spec.unit)
        after = stock_after(balance, quantity, kind)
        result.append(
            PlannedMovement(kind, quantity, occurred_at, "[DEMO] " + reason, balance, after)
        )
        balance = after
    if balance != spec.target:
        raise ValueError("Demo ledger does not reconcile")
    return result


def preview(anchor: datetime) -> dict:
    value, balances, types = Decimal(0), {unit: Decimal(0) for unit in ["PCS", "KG", "LITER"]}, {}
    for index, spec in enumerate(PRODUCTS):
        value += spec.target * Decimal(spec.cost)
        balances[spec.unit] += spec.target
        for movement in plan_product(spec, index, anchor):
            types[movement.movement_type] = types.get(movement.movement_type, 0) + 1
    return {
        "products": len(PRODUCTS),
        "active_products": sum(spec.active for spec in PRODUCTS),
        "movements": sum(types.values()),
        "movement_types": types,
        "low_stock": sum(
            spec.active and Decimal(spec.minimum) > 0 and spec.target < Decimal(spec.minimum)
            for spec in PRODUCTS
        ),
        "estimated_inventory_value_vnd": f"{value:.2f}",
        "stock_by_unit": {unit: f"{qty:.3f}" for unit, qty in balances.items()},
    }
