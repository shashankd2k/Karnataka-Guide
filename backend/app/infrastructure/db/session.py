"""
Async database engine, session factory, and FastAPI dependency.
"""

from functools import lru_cache
from typing import AsyncIterator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
import structlog
from app.core.config import Settings, get_settings

logger = structlog.get_logger("app.db.session")


@lru_cache()
def get_async_engine(settings: Optional[Settings] = None) -> AsyncEngine:
    """Create and cache the singleton async SQLAlchemy engine."""
    app_settings = settings or get_settings()
    logger.info(
        "creating_async_db_engine",
        host=app_settings.DB_HOST,
        port=app_settings.DB_PORT,
        database=app_settings.DB_NAME,
        user=app_settings.DB_USER,
    )
    return create_async_engine(
        app_settings.async_database_url,
        echo=False,
        pool_size=app_settings.DB_POOL_SIZE,
        max_overflow=app_settings.DB_MAX_OVERFLOW,
        pool_timeout=app_settings.DB_POOL_TIMEOUT,
        pool_recycle=app_settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
    )


def get_session_factory(
    engine: Optional[AsyncEngine] = None,
) -> async_sessionmaker[AsyncSession]:
    """Create an async sessionmaker bound to the given or default engine."""
    db_engine = engine or get_async_engine()
    return async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that provides an isolated AsyncSession per request."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db_engine() -> None:
    """Gracefully close and dispose the engine pool during shutdown."""
    engine = get_async_engine()
    await engine.dispose()
    get_async_engine.cache_clear()
    logger.info("async_db_engine_disposed")
