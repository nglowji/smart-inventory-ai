import logging
from time import perf_counter
from uuid import UUID, uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import error_response
from app.core.request_context import request_id

logger = logging.getLogger("smartinventory.http")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, api_prefix: str = ""):
        self.app = app
        self.api_prefix = api_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = (
            dict(scope.get("headers", []))
            .get(b"x-request-id", b"")
            .decode("ascii", errors="ignore")
        )
        try:
            correlation_id = str(UUID(incoming))
        except ValueError:
            correlation_id = str(uuid4())
        token = request_id.set(correlation_id)
        state = scope.setdefault("state", {})
        state["request_id"] = correlation_id
        status, started = 500, False
        start = perf_counter()

        async def correlated_send(message: Message) -> None:
            nonlocal status, started
            if message["type"] == "http.response.start":
                started, status = True, message["status"]
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"x-request-id"
                ]
                message["headers"] = [*headers, (b"x-request-id", correlation_id.encode())]
            await send(message)

        try:
            try:
                await self.app(scope, receive, correlated_send)
            except Exception as exc:
                state["error_code"] = "INTERNAL_ERROR"
                state["error_type"] = type(exc).__name__
                if started:
                    raise
                await error_response(500, "INTERNAL_ERROR", "Có lỗi máy chủ. Vui lòng thử lại.")(
                    scope, receive, correlated_send
                )
        finally:
            route = getattr(scope.get("route"), "path", "(unmatched)")
            # Included routers may expose a local template without their registered prefix.
            if (
                self.api_prefix
                and scope["path"].startswith(self.api_prefix + "/")
                and route != "(unmatched)"
                and not route.startswith(self.api_prefix + "/")
            ):
                route = self.api_prefix + route
            logger.info(
                "http_request",
                extra={
                    "request_id": correlation_id,
                    "method": scope["method"],
                    "route": route,
                    "status": status,
                    "duration_ms": round((perf_counter() - start) * 1000, 2),
                    "actor_id": state.get("actor_id"),
                    "error_code": state.get("error_code"),
                    "error_type": state.get("error_type"),
                },
            )
            request_id.reset(token)
