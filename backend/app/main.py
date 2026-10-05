"""
Main FastAPI application entry point and application factory.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Optional
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware
from app.infrastructure.db.health import check_db_health
from app.infrastructure.db.session import close_db_engine
from app.infrastructure.llm.ollama import close_ollama_provider


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifespan context."""
    settings = getattr(app.state, "settings", get_settings())
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_json=settings.LOG_JSON,
    )
    logger = structlog.get_logger("app.lifecycle")
    logger.info(
        "app_startup",
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        profile=settings.APP_PROFILE.value,
        debug=settings.DEBUG,
    )
    yield
    # Gracefully dispose database connection pool and persistent LLM HTTP pool on shutdown
    await close_ollama_provider()
    await close_db_engine()
    logger.info("app_shutdown", project=settings.PROJECT_NAME)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Create and configure a FastAPI application instance."""
    app_settings = settings or get_settings()

    app = FastAPI(
        title=app_settings.PROJECT_NAME,
        version=app_settings.VERSION,
        debug=app_settings.DEBUG,
        lifespan=lifespan,
    )

    # Store settings in state for access across handlers
    app.state.settings = app_settings

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-Audio-Duration-Seconds",
            "X-Audio-Sample-Rate",
            "X-Audio-Channels",
            "X-Language",
        ],
    )

    # 2. Request Correlation ID Middleware
    app.add_middleware(RequestIDMiddleware)

    # 3. Global Exception Handlers
    register_error_handlers(app)

    # 4. Root Health & Telemetry Probes
    @app.get("/health", tags=["System Probes"], summary="General Health Check")
    async def root_health() -> Dict[str, Any]:
        return {
            "status": "healthy",
            "profile": app_settings.APP_PROFILE.value,
            "version": app_settings.VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/live", tags=["System Probes"], summary="Liveness Probe")
    async def liveness_probe() -> Dict[str, str]:
        return {"status": "alive"}

    @app.get("/ready", tags=["System Probes"], summary="Readiness Probe")
    async def readiness_probe() -> JSONResponse:
        db_healthy = await check_db_health()
        payload = {
            "status": "ready" if db_healthy else "not_ready",
            "subsystems": {
                "app": "healthy",
                "database": "healthy" if db_healthy else "unhealthy",
            },
        }
        status_code = (
            status.HTTP_200_OK if db_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return JSONResponse(status_code=status_code, content=payload)

    @app.get("/version", tags=["System Probes"], summary="Version Probe")
    async def version_probe() -> Dict[str, str]:
        return {
            "project_name": app_settings.PROJECT_NAME,
            "version": app_settings.VERSION,
            "profile": app_settings.APP_PROFILE.value,
        }

    # 5. Mount API v1 Router
    app.include_router(api_router, prefix=app_settings.API_V1_STR)

    return app


# Default ASGI application instance
app = create_app()
