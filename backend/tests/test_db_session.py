"""
Unit tests for database session lifecycle and engine factory.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.infrastructure.db.session import (
    close_db_engine,
    get_async_engine,
    get_db_session,
    get_session_factory,
)


def test_get_async_engine_singleton():
    """Verify get_async_engine returns cached engine instance."""
    e1 = get_async_engine()
    e2 = get_async_engine()
    assert e1 is e2


def test_get_session_factory():
    """Verify sessionmaker creation."""
    factory = get_session_factory()
    assert factory is not None


@pytest.mark.asyncio
async def test_get_db_session_commit_on_success():
    """Verify session dependency commits transactions on normal exit."""
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session

    mock_factory = MagicMock(return_value=mock_session)

    with patch("app.infrastructure.db.session.get_session_factory", return_value=mock_factory):
        gen = get_db_session()
        session = await gen.__anext__()
        assert session is mock_session
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

        mock_session.commit.assert_awaited_once()
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_db_session_rollback_on_error():
    """Verify session dependency rolls back transactions on unhandled error."""
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session

    mock_factory = MagicMock(return_value=mock_session)

    with patch("app.infrastructure.db.session.get_session_factory", return_value=mock_factory):
        gen = get_db_session()
        session = await gen.__anext__()
        assert session is mock_session
        with pytest.raises(RuntimeError):
            await gen.athrow(RuntimeError("Simulated database operation failure!"))

        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()
