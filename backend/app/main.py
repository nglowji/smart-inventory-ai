from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.core.errors import error_response, install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.db.connection import build_engine, database_is_ready
from app.modules.ai.api import router as ai_router
from app.modules.audit.api import router as audit_router
from app.modules.auth.api import router as auth_router
from app.modules.catalog.api import router as catalog_router
from app.modules.inventory.api import router as inventory_router
from app.modules.reporting.api import router as reporting_router
from app.modules.users.api import router as users_router

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # Engine creation is lazy: a database outage must not prevent liveness.
        engine = build_engine(config)
        application.state.engine = engine
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title=config.app_name, version="0.5.0", lifespan=lifespan)
    application.state.settings = config
    install_error_handlers(application)
    application.include_router(auth_router, prefix=API_PREFIX)
    application.include_router(catalog_router, prefix=API_PREFIX)
    application.include_router(inventory_router, prefix=API_PREFIX)
    application.include_router(reporting_router, prefix=API_PREFIX)
    application.include_router(users_router, prefix=API_PREFIX)
    application.include_router(audit_router, prefix=API_PREFIX)
    application.include_router(ai_router, prefix=API_PREFIX)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    application.add_middleware(RequestContextMiddleware, api_prefix=API_PREFIX)

    @application.get("/health", tags=["Health"])
    def health():
        return {"status": "ok"}

    @application.get("/health/ready", tags=["Health"])
    def readiness(request: Request):
        if database_is_ready(request.app.state.engine):
            return {"status": "ready", "database": "available"}
        request.state.error_code = "DATABASE_UNAVAILABLE"
        return error_response(
            503,
            "DATABASE_UNAVAILABLE",
            "Chưa kết nối được cơ sở dữ liệu.",
            details={"database": "unavailable"},
        )

    return application


app = create_app()
