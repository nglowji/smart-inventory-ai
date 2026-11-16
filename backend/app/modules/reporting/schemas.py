from datetime import date, datetime
from typing import Literal

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
