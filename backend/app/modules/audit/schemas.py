from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

AuditEvent = Literal[
    "LOGIN_FAILED",
    "LOGIN_SUCCESS",
    "USER_CREATED",
    "USER_UPDATED",
    "USER_PASSWORD_RESET",
    "PASSWORD_CHANGED",
    "PRODUCT_ARCHIVED",
    "STOCK_ADJUSTED",
]


class AuditRead(BaseModel):
    id: UUID
    actor_id: UUID | None
    actor_email: str | None
    event_type: AuditEvent
    target_type: str
    target_id: UUID | None
    details: dict[str, str | bool]
    request_id: UUID | None
    created_at: datetime
