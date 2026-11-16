from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.db.connection import build_engine, database_is_ready


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # Engine creation is lazy: a database outage must not prevent liveness.
        engine = build_engine(config)
        application.state.engine = engine
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title=config.app_name, version="0.1.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
    )

    @application.get("/health", tags=["Health"])
    def health():
        return {"status": "ok"}

    @application.get("/health/ready", tags=["Health"])
    def readiness(request: Request):
        if database_is_ready(request.app.state.engine):
            return {"status": "ready", "database": "available"}
        request_id = str(uuid4())
        return JSONResponse(
            status_code=503,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "code": "DATABASE_UNAVAILABLE",
                    "message": "Chưa kết nối được cơ sở dữ liệu.",
                    "details": {"database": "unavailable"},
                    "request_id": request_id,
                }
            },
        )

    return application


app = create_app()
