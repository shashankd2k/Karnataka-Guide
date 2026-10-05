"""
Inexpensive database health and connectivity verification probes.
"""

import asyncio
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
import structlog
from app.infrastructure.db.session import get_async_engine

logger = structlog.get_logger("app.db.health")


async def check_db_health(
    engine: Optional[AsyncEngine] = None,
    timeout_seconds: float = 2.0,
) -> bool:
    """Execute a lightweight SELECT 1 query to verify active MySQL connectivity."""
    db_engine = engine or get_async_engine()
    try:
        async with asyncio.timeout(timeout_seconds):
            async with db_engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                scalar_val = result.scalar()
                if scalar_val == 1:
                    return True
                return False
    except Exception as exc:
        logger.warning(
            "db_health_check_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return False
