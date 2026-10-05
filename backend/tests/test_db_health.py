"""
Integration tests for database health probes and system readiness integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx
from app.infrastructure.db.health import check_db_health


@pytest.mark.asyncio
async def test_check_db_health_success():
    """Verify check_db_health returns True when SELECT 1 executes successfully."""
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_cm

    is_healthy = await check_db_health(engine=mock_engine)
    assert is_healthy is True


@pytest.mark.asyncio
async def test_check_db_health_failure():
    """Verify check_db_health returns False when connection fails without throwing."""
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=ConnectionRefusedError("Database connection refused"))
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_cm

    is_healthy = await check_db_health(engine=mock_engine)
    assert is_healthy is False


@pytest.mark.asyncio
async def test_ready_probe_healthy_db(async_client: httpx.AsyncClient):
    """Verify GET /ready returns 200 and healthy subsystems when DB is available."""
    with patch("app.main.check_db_health", return_value=True):
        response = await async_client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["subsystems"]["app"] == "healthy"
        assert data["subsystems"]["database"] == "healthy"


@pytest.mark.asyncio
async def test_ready_probe_unhealthy_db(async_client: httpx.AsyncClient):
    """Verify GET /ready returns 503 and unhealthy database status when DB fails."""
    with patch("app.main.check_db_health", return_value=False):
        response = await async_client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["subsystems"]["app"] == "healthy"
        assert data["subsystems"]["database"] == "unhealthy"


@pytest.mark.asyncio
async def test_live_probe_independent_of_db(async_client: httpx.AsyncClient):
    """Verify GET /live returns 200 even if database is unavailable."""
    with patch("app.main.check_db_health", return_value=False):
        response = await async_client.get("/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
