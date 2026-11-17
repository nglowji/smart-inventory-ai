from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dates import history_bounds
from app.db.models import AuditLog, User


def list_audit(
    session: Session,
    *,
    page: int,
    page_size: int,
    event_type: str | None,
    actor_id: UUID | None,
    date_from: date | None,
    date_to: date | None,
):
    statement = select(AuditLog, User.email).outerjoin(User, User.id == AuditLog.actor_id)
    if event_type:
        statement = statement.where(AuditLog.event_type == event_type)
    if actor_id:
        statement = statement.where(AuditLog.actor_id == actor_id)
    start, end = history_bounds(date_from, date_to)
    if start is not None:
        statement = statement.where(AuditLog.created_at >= start)
    if end is not None:
        statement = statement.where(AuditLog.created_at < end)
    total = session.scalar(select(func.count()).select_from(statement.subquery()))
    rows = session.execute(
        statement.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [
            {
                "id": row.id,
                "actor_id": row.actor_id,
                "actor_email": email,
                "event_type": row.event_type,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "details": row.details,
                "request_id": row.request_id,
                "created_at": row.created_at,
            }
            for row, email in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
