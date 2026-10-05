"""
Integration tests for root and versioned health/liveness/readiness probes.
"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_root_health_endpoint(async_client: httpx.AsyncClient):
    """Verify GET /health returns application status."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["profile"] == "dev"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_liveness_probe(async_client: httpx.AsyncClient):
    """Verify GET /live returns alive status."""
    response = await async_client.get("/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_probe(async_client: httpx.AsyncClient):
    """Verify GET /ready returns application readiness."""
    response = await async_client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "subsystems" in data
    assert data["subsystems"]["app"] == "healthy"


@pytest.mark.asyncio
async def test_version_probe(async_client: httpx.AsyncClient):
    """Verify GET /version returns version and project info."""
    response = await async_client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "0.1.0-test"
    assert "Karnataka" in data["project_name"]


@pytest.mark.asyncio
async def test_api_v1_health_probe(async_client: httpx.AsyncClient):
    """Verify GET /api/v1/health returns versioned health status."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["api_version"] == "v1"
    assert data["subsystems"]["app"] == "healthy"
