from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.dates import date_bounds


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(default="Cuộc trò chuyện mới", min_length=1, max_length=100)


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=2000)
    client_request_id: UUID = Field(default_factory=uuid4)


class Source(BaseModel):
    type: str
    sku: str | None = None
    as_of: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    client_request_id: UUID
    role: Literal["USER", "ASSISTANT"]
    content: str
    sources: list[Source]
    tool_calls: list[str]
    created_at: datetime


class Answer(BaseModel):
    message_id: UUID
    answer: str
    sources: list[Source]
    tool_calls: list[str]


class ToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SkuArgs(ToolArgs):
    sku: str = Field(min_length=1, max_length=64)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value):
        return value.upper()


class LimitArgs(ToolArgs):
    limit: int = Field(default=10, ge=1, le=20, strict=True)


class SearchArgs(LimitArgs):
    query: str = Field(min_length=1, max_length=100)


class OutboundArgs(ToolArgs):
    from_date: date
    to_date: date
    sku: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def valid_range(self):
        date_bounds(self.from_date, self.to_date)
        if self.sku:
            self.sku = self.sku.upper()
        return self


class RecentArgs(LimitArgs):
    sku: str | None = Field(default=None, min_length=1, max_length=64)


class ReplenishmentArgs(SkuArgs):
    lookback_days: int = Field(default=30, ge=1, le=366, strict=True)
