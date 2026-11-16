from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.errors import DomainError
from app.modules.inventory.idempotency import request_fingerprint
from app.modules.inventory.policies import (
    MAX_STOCK,
    require_movement_permission,
    stock_after,
    validate_quantity,
)
from app.modules.inventory.schemas import MovementCreate


@pytest.mark.parametrize("unit,quantity", [("PCS", "2"), ("KG", "1.234"), ("LITER", "0.001")])
def test_valid_unit_quantities(unit, quantity):
    validate_quantity(Decimal(quantity), unit)


@pytest.mark.parametrize("quantity", ["0", "-1", "NaN", "Infinity", "0.0001", "100000000000"])
def test_quantity_policy_rejects_invalid_values(quantity):
    with pytest.raises(DomainError) as caught:
        validate_quantity(Decimal(quantity), "KG")
    assert caught.value.code == "INVALID_QUANTITY"


def test_pcs_requires_integer():
    with pytest.raises(DomainError) as caught:
        validate_quantity(Decimal("1.5"), "PCS")
    assert caught.value.code == "INVALID_QUANTITY_UNIT"


@pytest.mark.parametrize("kind", ["OUT", "ADJUST_OUT"])
def test_outbound_cannot_go_below_zero(kind):
    with pytest.raises(DomainError) as caught:
        stock_after(Decimal("2"), Decimal("3"), kind)
    assert caught.value.code == "INSUFFICIENT_STOCK"
    assert stock_after(Decimal("2"), Decimal("2"), kind) == Decimal("0")


@pytest.mark.parametrize("kind", ["IN", "ADJUST_IN"])
def test_inbound_cannot_overflow_storage(kind):
    with pytest.raises(DomainError) as caught:
        stock_after(MAX_STOCK, Decimal("0.001"), kind)
    assert caught.value.status == 422


def test_decimal_arithmetic_preserves_small_quantities():
    assert stock_after(Decimal("0.300"), Decimal("0.100"), "OUT") == Decimal("0.200")


@pytest.mark.parametrize(
    "role,kind",
    [("VIEWER", "IN"), ("STAFF", "ADJUST_IN"), ("STAFF", "ADJUST_OUT"), ("UNKNOWN", "IN")],
)
def test_write_permission_is_an_allowlist(role, kind):
    with pytest.raises(DomainError) as caught:
        require_movement_permission(role, kind)
    assert caught.value.status == 403


def test_request_identity_is_canonical_and_actor_scoped():
    product_id, actor_id = uuid4(), uuid4()
    payload = MovementCreate(
        product_id=product_id, movement_type="IN", quantity="5", reason="  initial stock  "
    )
    equivalent = MovementCreate(
        product_id=product_id, movement_type="IN", quantity="5.000", reason="initial stock"
    )
    assert request_fingerprint(payload, actor_id) == request_fingerprint(equivalent, actor_id)
    assert request_fingerprint(payload, actor_id) != request_fingerprint(payload, uuid4())
