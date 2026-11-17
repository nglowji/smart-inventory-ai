import logging
from datetime import timedelta
from time import perf_counter
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import DomainError
from app.core.request_context import request_id
from app.db.models import AiConversation, AiMessage, AuditLog, User
from app.modules.ai.memory import build_context
from app.modules.ai.policies import requests_write
from app.modules.ai.queries import completed_turn, owned_conversation, recent_context
from app.modules.ai.rendering import CLARIFY_ANSWER, READ_ONLY_ANSWER, render_result
from app.modules.ai.schemas import Answer, ConversationCreate, MessageCreate
from app.modules.ai.tools import REGISTRY, execute_tool
from app.modules.audit.service import record_event

logger = logging.getLogger("smartinventory.http")


def create_conversation(session: Session, user_id: UUID, payload: ConversationCreate):
    conversation = AiConversation(user_id=user_id, title=payload.title)
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def as_answer(message: AiMessage) -> Answer:
    return Answer(
        message_id=message.id,
        answer=message.content,
        sources=message.sources,
        tool_calls=message.tool_calls,
    )


def replay(session: Session, conversation_id: UUID, payload: MessageCreate):
    previous = completed_turn(session, conversation_id, payload.client_request_id)
    if previous:
        question = session.scalar(
            select(AiMessage.content).where(
                AiMessage.conversation_id == conversation_id,
                AiMessage.client_request_id == payload.client_request_id,
                AiMessage.role == "USER",
            )
        )
        if question != payload.message:
            raise DomainError(
                409, "IDEMPOTENCY_CONFLICT", "Mã gửi lại đã được dùng cho câu hỏi khác."
            )
        return as_answer(previous)
    return None


def acquire_turn(session, user_id, conversation_id, payload, settings):
    # Shared across workers; released before the provider/network call.
    session.execute(select(func.pg_advisory_xact_lock(1430081, user_id.int & 0x7FFFFFFF)))
    conversation = owned_conversation(session, conversation_id, user_id, lock=True)
    previous = replay(session, conversation_id, payload)
    if previous:
        session.commit()
        return previous, None, []
    now = session.scalar(select(func.clock_timestamp()))
    if conversation.pending_until and conversation.pending_until > now:
        raise DomainError(
            409, "AI_BUSY", "Cuộc trò chuyện đang xử lý câu hỏi trước. Vui lòng chờ rồi thử lại."
        )
    count = session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.actor_id == user_id,
            AuditLog.event_type == "AI_REQUESTED",
            AuditLog.created_at > now - timedelta(minutes=1),
        )
    )
    if count >= settings.ai_requests_per_minute:
        raise DomainError(
            429, "RATE_LIMITED", "Bạn đã đạt giới hạn câu hỏi trong một phút. Vui lòng thử lại sau."
        )
    lease = uuid4()
    conversation.pending_request_id = lease
    conversation.pending_until = now + timedelta(seconds=60)
    context = recent_context(session, conversation_id)
    record_event(
        session,
        "AI_REQUESTED",
        actor_id=user_id,
        target_type="ai_conversation",
        target_id=conversation_id,
    )
    session.commit()
    return None, lease, context


def release_turn(session, user_id, conversation_id, lease, error_code=None, traces=()):
    session.rollback()
    session.execute(
        update(AiConversation)
        .where(
            AiConversation.id == conversation_id,
            AiConversation.user_id == user_id,
            AiConversation.pending_request_id == lease,
        )
        .values(pending_request_id=None, pending_until=None)
    )
    # Release independently, including when the audit subsystem itself caused the failure.
    session.commit()
    if not error_code:
        return
    try:
        record_event(
            session,
            "AI_RESPONSE_FAILED",
            actor_id=user_id,
            target_type="ai_conversation",
            target_id=conversation_id,
            details={"code": error_code},
        )
        for trace in traces:
            record_event(
                session,
                "AI_TOOL_CALLED",
                actor_id=user_id,
                target_type="ai_conversation",
                target_id=conversation_id,
                details=trace,
            )
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error(
            "ai_failure_audit_unavailable",
            extra={
                "request_id": request_id.get(),
                "actor_id": str(user_id),
                "error_type": type(exc).__name__,
                "error_code": error_code,
            },
        )


def send_message(
    session: Session,
    user: User,
    conversation_id: UUID,
    payload: MessageCreate,
    settings: Settings,
    provider,
) -> Answer:
    user_id = user.id
    role = user.role
    previous, lease, context = acquire_turn(session, user_id, conversation_id, payload, settings)
    if previous:
        return previous
    traces, results = [], []
    started = perf_counter()
    try:
        if requests_write(payload.message):
            answer = READ_ONLY_ANSWER
        else:
            calls = provider.plan(context, payload.message)
            if not isinstance(calls, list) or len(calls) > 3:
                raise DomainError(503, "AI_RESPONSE_INVALID", "Model vượt giới hạn công cụ.")
            for call in calls:
                if call.name not in REGISTRY:
                    raise DomainError(
                        503, "AI_RESPONSE_INVALID", "Model đề xuất công cụ không hợp lệ."
                    )
                try:
                    REGISTRY[call.name][0].model_validate(call.arguments)
                except DomainError:
                    raise ValueError("Invalid model date range") from None
            for call in calls:
                remaining = 30 - (perf_counter() - started)
                if remaining < 1:
                    raise DomainError(
                        503,
                        "AI_PROVIDER_UNAVAILABLE",
                        "Tra cứu AI mất quá nhiều thời gian. Vui lòng thử lại.",
                    )
                tick = perf_counter()
                trace = {"tool_name": call.name, "success": False, "latency_ms": 0}
                traces.append(trace)
                try:
                    result = execute_tool(
                        session.get_bind(), call.name, call.arguments, timeout_seconds=remaining
                    )
                finally:
                    trace["latency_ms"] = round((perf_counter() - tick) * 1000)
                trace["success"] = True
                if call.name == "get_system_help":
                    result["data"]["current_role"] = role
                results.append(result)
            answer = (
                "\n\n".join(render_result(result) for result in results)
                if results
                else CLARIFY_ANSWER
            )
        conversation = owned_conversation(session, conversation_id, user_id, lock=True)
        now = session.scalar(select(func.clock_timestamp()))
        if conversation.pending_request_id != lease or conversation.pending_until <= now:
            raise DomainError(
                409,
                "AI_BUSY",
                "Lượt xử lý đã hết hạn. Hãy tải lại cuộc trò chuyện trước khi thử lại.",
            )
        # Never persist half a turn. Ordering is explicit, independent of UUID values.
        session.add(
            AiMessage(
                conversation_id=conversation_id,
                client_request_id=payload.client_request_id,
                role="USER",
                content=payload.message,
                created_at=now,
            )
        )
        response = AiMessage(
            id=uuid4(),
            conversation_id=conversation_id,
            client_request_id=payload.client_request_id,
            role="ASSISTANT",
            content=answer,
            sources=[result["source"] for result in results],
            tool_calls=[result["tool"] for result in results],
            planner_context=build_context(results),
            created_at=now + timedelta(microseconds=1),
        )
        session.add(response)
        conversation.pending_request_id, conversation.pending_until = None, None
        conversation.updated_at = now
        if conversation.title == "Cuộc trò chuyện mới":
            conversation.title = payload.message[:100]
        for trace in traces:
            record_event(
                session,
                "AI_TOOL_CALLED",
                actor_id=user_id,
                target_type="ai_conversation",
                target_id=conversation_id,
                details=trace,
            )
        session.commit()
        session.refresh(response)
        return as_answer(response)
    except (ValidationError, ValueError, TypeError, AttributeError):
        release_turn(session, user_id, conversation_id, lease, "AI_RESPONSE_INVALID", traces)
        raise DomainError(
            503, "AI_RESPONSE_INVALID", "Model trả tham số không hợp lệ. Vui lòng thử lại."
        ) from None
    except Exception as exc:
        code = exc.code if isinstance(exc, DomainError) else "AI_PROVIDER_UNAVAILABLE"
        release_turn(session, user_id, conversation_id, lease, code, traces)
        if isinstance(exc, DomainError):
            raise
        raise DomainError(
            503,
            "AI_PROVIDER_UNAVAILABLE",
            "Chưa truy vấn được dữ liệu cho trợ lý. Vui lòng thử lại.",
        ) from None
