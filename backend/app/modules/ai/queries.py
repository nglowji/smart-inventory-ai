from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.db.models import AiConversation, AiMessage
from app.db.pagination import paginate


def owned_conversation(session: Session, conversation_id: UUID, user_id: UUID, *, lock=False):
    query = select(AiConversation).where(
        AiConversation.id == conversation_id, AiConversation.user_id == user_id
    )
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    conversation = session.scalar(query)
    if conversation is None:
        raise DomainError(404, "CONVERSATION_NOT_FOUND", "Không tìm thấy cuộc trò chuyện.")
    return conversation


def list_conversations(session: Session, user_id: UUID, page: int, page_size: int):
    return paginate(
        session,
        select(AiConversation)
        .where(AiConversation.user_id == user_id)
        .order_by(AiConversation.updated_at.desc(), AiConversation.id.desc()),
        page,
        page_size,
    )


def list_messages(
    session: Session, conversation_id: UUID, user_id: UUID, page: int, page_size: int
):
    owned_conversation(session, conversation_id, user_id)
    result = paginate(
        session,
        select(AiMessage)
        .where(AiMessage.conversation_id == conversation_id)
        .order_by(AiMessage.created_at.desc(), AiMessage.id.desc()),
        page,
        page_size,
    )
    # Pagination walks backwards; each returned page reads in chronological order.
    result["items"].reverse()
    return result


def completed_turn(session: Session, conversation_id: UUID, request_id: UUID):
    return session.scalar(
        select(AiMessage).where(
            AiMessage.conversation_id == conversation_id,
            AiMessage.client_request_id == request_id,
            AiMessage.role == "ASSISTANT",
        )
    )


def recent_context(session: Session, conversation_id: UUID) -> list[dict]:
    # No DB product names, movement notes, assistant text or credentials go to the model.
    rows = session.scalars(
        select(AiMessage)
        .where(AiMessage.conversation_id == conversation_id, AiMessage.role == "USER")
        .order_by(AiMessage.created_at.desc(), AiMessage.id.desc())
        .limit(4)
    ).all()
    return [{"role": "user", "content": row.content[:500]} for row in reversed(rows)]
