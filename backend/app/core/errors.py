from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException

from app.core.request_context import request_id


class DomainError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def error_response(status: int, code: str, message: str, details: dict | None = None):
    correlation_id = request_id.get() or str(uuid4())
    return JSONResponse(
        status_code=status,
        headers={"X-Request-ID": correlation_id},
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "request_id": correlation_id,
            }
        },
    )


def install_error_handlers(app: FastAPI):
    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError):
        request.state.error_code = exc.code
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        request.state.error_code = "VALIDATION_ERROR"
        # Never echo raw input (login passwords, for example).
        return error_response(422, "VALIDATION_ERROR", "Dữ liệu không hợp lệ.")

    @app.exception_handler(IntegrityError)
    async def integrity_error(request: Request, exc: IntegrityError):
        request.state.error_code = "DATA_CONFLICT"
        return error_response(409, "DATA_CONFLICT", "Dữ liệu xung đột với ràng buộc lưu trữ.")

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        request.state.error_code = "DATABASE_UNAVAILABLE"
        return error_response(503, "DATABASE_UNAVAILABLE", "Chưa truy cập được dữ liệu.")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        codes = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
        request.state.error_code = codes.get(exc.status_code, "BAD_REQUEST")
        return error_response(
            exc.status_code,
            codes.get(exc.status_code, "BAD_REQUEST"),
            "Yêu cầu không được chấp nhận.",
        )
