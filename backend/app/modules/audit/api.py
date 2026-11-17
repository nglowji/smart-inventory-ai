from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.schemas import Page
from app.db.session import get_session
from app.modules.audit.queries import list_audit
from app.modules.audit.schemas import AuditEvent, AuditRead
from app.modules.auth.dependencies import admin_user

router = APIRouter(prefix="/audit", tags=["Audit"], dependencies=[Depends(admin_user)])


@router.get("", response_model=Page[AuditRead])
def audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    event_type: AuditEvent | None = None,
    actor_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    session: Session = Depends(get_session),
):
    return list_audit(
        session,
        page=page,
        page_size=page_size,
        event_type=event_type,
        actor_id=actor_id,
        date_from=date_from,
        date_to=date_to,
    )
