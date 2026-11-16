from decimal import Decimal
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

Name120 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Name200 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Name255 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Sku = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1, max_length=64)
]
Quantity = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=3, allow_inf_nan=False)]
Money = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2, allow_inf_nan=False)]
Unit = Literal["PCS", "KG", "LITER"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def require_decimal_strings(cls, value, info):
        if info.field_name in {"min_stock", "unit_cost_vnd"}:
            if value is not None and not isinstance(value, str):
                raise ValueError("Decimal values must be JSON strings")
        return value


class PatchInput(Input):
    @field_validator("*", mode="before")
    @classmethod
    def reject_nonnullable_null(cls, value, info):
        nullable = {"category_id", "default_supplier_id", "email", "phone"}
        if value is None and info.field_name not in nullable:
            raise ValueError("This field cannot be null")
        return value


class CategoryCreate(Input):
    name: Name120


class CategoryPatch(PatchInput):
    name: Name120 | None = None
    is_active: bool | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    is_active: bool


class SupplierCreate(Input):
    name: Name200
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None
    email: EmailStr | None = None


class SupplierPatch(PatchInput):
    name: Name200 | None = None
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None
    email: EmailStr | None = None
    is_active: bool | None = None


class SupplierRead(CategoryRead):
    phone: str | None
    email: str | None


class ProductCreate(Input):
    sku: Sku
    name: Name255
    category_id: UUID | None = None
    default_supplier_id: UUID | None = None
    unit: Unit
    min_stock: Quantity = Decimal("0")
    lead_time_days: int = Field(default=7, ge=0, le=2147483647, strict=True)
    unit_cost_vnd: Money = Decimal("0")


class ProductPatch(PatchInput):
    sku: Sku | None = None
    name: Name255 | None = None
    category_id: UUID | None = None
    default_supplier_id: UUID | None = None
    unit: Unit | None = None
    min_stock: Quantity | None = None
    lead_time_days: Annotated[int, Field(ge=0, le=2147483647, strict=True)] | None = None
    unit_cost_vnd: Money | None = None


class ProductRead(BaseModel):
    id: UUID
    sku: str
    name: str
    category_id: UUID | None
    default_supplier_id: UUID | None
    unit: Unit
    min_stock: str
    lead_time_days: int
    unit_cost_vnd: str
    on_hand: str
    is_active: bool


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
