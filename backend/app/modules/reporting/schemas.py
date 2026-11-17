from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

Unit = Literal["PCS", "KG", "LITER"]


class DashboardSummary(BaseModel):
    total_active_skus: int
    low_stock_count: int
    estimated_inventory_value_vnd: str
    movement_count: int
    stock_by_unit: dict[Unit, str]
    date_from: date
    date_to: date
    timezone: str
    as_of: datetime


class FlowTotals(BaseModel):
    inbound: str
    outbound: str


class FlowItem(FlowTotals):
    date: date
    unit: Unit


class DashboardFlow(BaseModel):
    items: list[FlowItem]
    totals: dict[Unit, FlowTotals]
    date_from: date
    date_to: date
    timezone: str
    as_of: datetime


class InventoryHealth(BaseModel):
    healthy: int
    low: int
    out_of_stock: int


class CategoryValue(BaseModel):
    key: str
    name: str
    value_vnd: str
    sku_count: int


class MovementCount(BaseModel):
    movement_type: Literal["IN", "OUT", "ADJUST_IN", "ADJUST_OUT"]
    count: int


class DailyActivity(BaseModel):
    date: date
    count: int


class OutboundProduct(BaseModel):
    product_id: UUID
    sku: str
    name: str
    unit: Unit
    quantity: str


class DashboardInsights(BaseModel):
    health: InventoryHealth
    archived_skus: int
    without_outbound_skus: int
    category_values: list[CategoryValue]
    estimated_inventory_value_vnd: str
    movement_types: list[MovementCount]
    daily_activity: list[DailyActivity]
    top_outbound: dict[Unit, list[OutboundProduct]]
    date_from: date
    date_to: date
    timezone: str
    as_of: datetime
    has_demo_data: bool
