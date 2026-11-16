from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MovementRead(BaseModel):
    id: UUID
    product_id: UUID
    sku: str
    name: str
    unit: Literal["PCS", "KG", "LITER"]
    movement_type: Literal["IN", "OUT", "ADJUST_IN", "ADJUST_OUT"]
    quantity: str
    stock_before: str
    stock_after: str
    reason: str | None
    supplier_id: UUID | None
    reference_code: str | None
    actor_id: UUID
    actor_email: str
    occurred_at: datetime


class MovementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    product_id: UUID
    movement_type: Literal["IN", "OUT", "ADJUST_IN", "ADJUST_OUT"]
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3, allow_inf_nan=False)
    reason: str | None = Field(default=None, max_length=2000)
    supplier_id: UUID | None = None
    reference_code: str | None = Field(default=None, max_length=50)

    @field_validator("quantity", mode="before")
    @classmethod
    def quantity_string(cls, value):
        if not isinstance(value, str):
            raise ValueError("Quantity must be a decimal string")
        return value

    @model_validator(mode="after")
    def validate_type_fields(self):
        self.reason = self.reason or None
        self.reference_code = self.reference_code or None
        if self.movement_type == "OUT" and not self.reason:
            raise ValueError("OUT requires a reason")
        if self.movement_type.startswith("ADJUST") and len(self.reason or "") < 10:
            raise ValueError("Adjustments require a reason of at least 10 characters")
        if self.supplier_id and self.movement_type != "IN":
            raise ValueError("Supplier only applies to IN movements")
        return self
