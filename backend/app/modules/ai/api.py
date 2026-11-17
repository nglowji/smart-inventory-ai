from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.schemas import Page
from app.db.models import User
from app.db.session import get_session
from app.modules.ai.provider import availability, configured_provider
from app.modules.ai.queries import list_conversations, list_messages, owned_conversation
from app.modules.ai.schemas import (
    Answer,
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from app.modules.ai.service import create_conversation, replay, send_message
from app.modules.auth.dependencies import current_user

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.get("/status")
def status(request: Request, user: User = Depends(current_user)):
    return availability(request.app.state.settings)


@router.get("/conversations", response_model=Page[ConversationRead])
def conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    return list_conversations(session, user.id, page, page_size)


@router.post("/conversations", response_model=ConversationRead, status_code=201)
def create(
    payload: ConversationCreate,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    return create_conversation(session, user.id, payload)


@router.get("/conversations/{conversation_id}/messages", response_model=Page[MessageRead])
def messages(
    conversation_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=50),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    return list_messages(session, conversation_id, user.id, page, page_size)


@router.post("/conversations/{conversation_id}/messages", response_model=Answer)
def send(
    conversation_id: UUID,
    payload: MessageCreate,
    request: Request,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    # Ownership is checked before provider configuration to avoid leaking session existence.
    owned_conversation(session, conversation_id, user.id)
    previous = replay(session, conversation_id, payload)
    if previous:
        return previous
    settings = request.app.state.settings
    provider = getattr(request.app.state, "ai_provider_override", None) or configured_provider(
        settings
    )
    return send_message(session, user, conversation_id, payload, settings, provider)
