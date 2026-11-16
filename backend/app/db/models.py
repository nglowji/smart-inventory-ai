"""Relational model. Movement writes are implemented in Phase 2."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('ADMIN','STAFF','VIEWER')", name="role"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("unit IN ('PCS','KG','LITER')", name="unit"),
        CheckConstraint("min_stock >= 0", name="min_stock"),
        CheckConstraint("lead_time_days >= 0", name="lead_time"),
        CheckConstraint("unit_cost_vnd >= 0", name="unit_cost"),
        CheckConstraint("sku = upper(trim(sku)) AND length(sku) > 0", name="sku_normalized"),
        Index("ix_products_is_active_name", "is_active", "name"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"))
    default_supplier_id: Mapped[UUID | None] = mapped_column(ForeignKey("suppliers.id"))
    unit: Mapped[str] = mapped_column(String(10))
    min_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), server_default="0")
    lead_time_days: Mapped[int] = mapped_column(server_default="7")
    unit_cost_vnd: Mapped[Decimal] = mapped_column(Numeric(18, 2), server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    balance: Mapped["StockBalance"] = relationship(back_populates="product", uselist=False)


class StockBalance(Base):
    __tablename__ = "stock_balances"
    __table_args__ = (CheckConstraint("on_hand >= 0", name="nonnegative"),)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), primary_key=True)
    on_hand: Mapped[Decimal] = mapped_column(Numeric(14, 3), server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    product: Mapped[Product] = relationship(back_populates="balance")


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("movement_type IN ('IN','OUT','ADJUST_IN','ADJUST_OUT')", name="type"),
        CheckConstraint("quantity > 0", name="quantity"),
        CheckConstraint("stock_before >= 0 AND stock_after >= 0", name="nonnegative"),
        Index("ix_movements_product_date", "product_id", "occurred_at", "id"),
        Index("ix_movements_type_date", "movement_type", "occurred_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    supplier_id: Mapped[UUID | None] = mapped_column(ForeignKey("suppliers.id"))
    movement_type: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    stock_before: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    stock_after: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    reason: Mapped[str | None] = mapped_column(Text)
    reference_code: Mapped[str | None] = mapped_column(String(50))
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
