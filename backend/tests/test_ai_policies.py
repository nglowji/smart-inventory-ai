from decimal import Decimal

import pytest

from app.modules.ai.policies import replenishment, requests_write


def calculate(**changes):
    return replenishment(
        **{
            "on_hand": Decimal("12"),
            "min_stock": Decimal("10"),
            "outbound": Decimal("120"),
            "movement_count": 1,
            "lead_time_days": 5,
            "lookback_days": 30,
            "unit": "PCS",
            **changes,
        }
    )


def test_replenishment_acceptance_case_and_round_up():
    result = calculate()
    assert result["suggested_qty"] == "18"
    assert result["avg_daily_out"] == "4"
    assert result["insufficient_history"] is False
    assert calculate(outbound=Decimal("121"))["suggested_qty"] == "19"
    assert calculate(outbound=Decimal("121"), unit="KG")["suggested_qty"] == "18.167"
    assert calculate(on_hand=Decimal("1000"))["suggested_qty"] == "0"


def test_no_outbound_is_not_reported_as_a_zero_demand_forecast():
    result = calculate(outbound=Decimal(0), movement_count=0, on_hand=Decimal("3"))
    assert result["insufficient_history"] is True
    assert result["avg_daily_out"] is None
    assert result["suggested_qty"] == "7"


@pytest.mark.parametrize(
    "question", ["Hãy xuất 5 SP001", "Nhập kho SP001", "Cập nhật tồn thành 100", "Xóa sản phẩm"]
)
def test_mutation_requests_are_refused(question):
    assert requests_write(question)


def test_outbound_report_is_not_a_mutation():
    assert not requests_write("Tổng xuất hôm nay là bao nhiêu?")
