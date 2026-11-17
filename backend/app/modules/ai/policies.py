import re
import unicodedata
from decimal import ROUND_CEILING, Decimal


def fold_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).lower().replace("đ", "d")
    return "".join(char for char in normalized if not unicodedata.combining(char))


def requests_write(message: str) -> bool:
    normalized = fold_text(message)
    return bool(
        re.search(
            r"\b(nhap kho|xuat kho|cap nhat|xoa|dat mua|tao giao dich|sua ton|doi ton)\b"
            r"|\b(hay|vui long|giup toi|thuc hien)\s+(nhap|xuat|sua|them)\b"
            r"|\b(nhap|xuat)\s+\d+\b",
            normalized,
        )
    )


def replenishment(
    *,
    on_hand: Decimal,
    min_stock: Decimal,
    outbound: Decimal,
    movement_count: int,
    lead_time_days: int,
    lookback_days: int,
    unit: str,
) -> dict:
    insufficient = movement_count == 0
    average = outbound / Decimal(lookback_days) if not insufficient else None
    target = min_stock if insufficient else average * Decimal(lead_time_days) + min_stock
    step = Decimal("1") if unit == "PCS" else Decimal("0.001")
    suggested = max(Decimal("0"), target - on_hand).quantize(step, rounding=ROUND_CEILING)
    return {
        "outbound_qty_period": str(outbound),
        "avg_daily_out": str(average) if average is not None else None,
        "lead_time_days": lead_time_days,
        "min_stock": str(min_stock),
        "on_hand": str(on_hand),
        "target_stock": str(target),
        "suggested_qty": str(suggested),
        "lookback_days": lookback_days,
        "insufficient_history": insufficient,
        "assumptions": "Tồn an toàn = ngưỡng tối thiểu; chưa xét hàng đang về, mùa vụ và MOQ.",
    }
