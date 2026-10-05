"""
Integration tests for RequestIDMiddleware and correlation tracking.
"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_request_id_generated_when_missing(async_client: httpx.AsyncClient):
    """Verify that a request ID is automatically generated if not provided."""
    response = await async_client.get("/live")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    req_id = response.headers["x-request-id"]
    assert len(req_id) == 32  # 32-char hex UUID


@pytest.mark.asyncio
async def test_request_id_preserved_when_valid(async_client: httpx.AsyncClient):
    """Verify that an incoming valid request ID is preserved and echoed back."""
    custom_id = "karnataka-guide-req-12345"
    response = await async_client.get("/live", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == custom_id


@pytest.mark.asyncio
async def test_request_id_replaced_when_unsafe(async_client: httpx.AsyncClient):
    """Verify that unsafe/malicious request IDs are replaced with a clean generated UUID."""
    unsafe_id = "<script>alert('xss')</script>"
    response = await async_client.get("/live", headers={"X-Request-ID": unsafe_id})
    assert response.status_code == 200
    returned_id = response.headers.get("x-request-id")
    assert returned_id != unsafe_id
    assert len(returned_id) == 32
