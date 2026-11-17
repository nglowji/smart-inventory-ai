from uuid import UUID

from sqlalchemy.orm import Session

from app.core.request_context import request_id
from app.db.models import AuditLog

# Metadata is explicitly allowlisted; never accept arbitrary request payloads.
EVENT_FIELDS = {
    "LOGIN_FAILED": {"reason"},
    "LOGIN_SUCCESS": set(),
    "USER_CREATED": {"role"},
    "USER_UPDATED": {"old_role", "new_role", "old_active", "new_active"},
    "USER_PASSWORD_RESET": set(),
    "PASSWORD_CHANGED": set(),
    "PRODUCT_ARCHIVED": {"sku"},
    "STOCK_ADJUSTED": {"product_id", "movement_type", "quantity"},
    "AI_REQUESTED": set(),
    "AI_TOOL_CALLED": {"tool_name", "success", "latency_ms"},
    "AI_RESPONSE_FAILED": {"code"},
}


def record_event(
    session: Session,
    event: str,
    *,
    actor_id: UUID | None,
    target_type: str,
    target_id: UUID | None = None,
    details: dict | None = None,
) -> None:
    allowed = EVENT_FIELDS[event]
    metadata = details or {}
    if set(metadata) - allowed:
        raise ValueError("Audit metadata contains unsupported fields")
    correlation_id = request_id.get()
    session.add(
        AuditLog(
            actor_id=actor_id,
            event_type=event,
            target_type=target_type,
            target_id=target_id,
            details=metadata,
            request_id=UUID(correlation_id) if correlation_id else None,
        )
    )
