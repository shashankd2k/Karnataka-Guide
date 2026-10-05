"""
Health and telemetry probes under /api/v1 namespace.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.core.config import Settings, get_settings
from app.infrastructure.db.health import check_db_health

router = APIRouter()


@router.get("/health", summary="API v1 Health Probe")
async def get_v1_health(settings: Settings = Depends(get_settings)) -> JSONResponse:
    """Return health status under the /api/v1 routing namespace."""
    db_healthy = await check_db_health()
    payload = {
        "status": "healthy" if db_healthy else "degraded",
        "api_version": "v1",
        "app_version": settings.VERSION,
        "profile": settings.APP_PROFILE.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subsystems": {
            "app": "healthy",
            "database": "healthy" if db_healthy else "unhealthy",
        },
    }
    status_code = status.HTTP_200_OK if db_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=payload)
