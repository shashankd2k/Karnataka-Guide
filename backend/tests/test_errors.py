"""
Integration tests for global exception handlers and standardized error envelopes.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
import pytest
import httpx

from app.core.errors import (
    AppException,
    ConflictException,
    ForbiddenException,
    NotFoundError,
    ServiceUnavailableException,
    UnauthorizedException,
    ValidationException,
)
from app.main import create_app

# Router with synthetic test endpoints for triggering exception cases
error_test_router = APIRouter(prefix="/test-errors", tags=["Error Tests"])


class DummyPayload(BaseModel):
    name: str = Field(min_length=3)
    age: int = Field(ge=0)


@error_test_router.get("/not-found")
async def trigger_not_found():
    raise NotFoundError("Custom item not found.", details={"item_id": 42})


@error_test_router.get("/unauthorized")
async def trigger_unauthorized():
    raise UnauthorizedException()


@error_test_router.get("/forbidden")
async def trigger_forbidden():
    raise ForbiddenException()


@error_test_router.get("/conflict")
async def trigger_conflict():
    raise ConflictException("Entity already exists.")


@error_test_router.get("/unavailable")
async def trigger_unavailable():
    raise ServiceUnavailableException()


@error_test_router.post("/validation")
async def trigger_validation(payload: DummyPayload):
    return {"status": "ok", "name": payload.name}


@error_test_router.get("/unhandled-500")
async def trigger_unhandled():
    raise RuntimeError("Simulated unexpected crash in business logic!")


@pytest.fixture
def error_app(test_settings):
    """App instance with error test router mounted."""
    app = create_app(settings=test_settings)
    app.include_router(error_test_router)
    return app


@pytest.fixture
async def error_client(error_app):
    """Async client connected to error testing app."""
    transport = httpx.ASGITransport(app=error_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_404_route_not_found(async_client: httpx.AsyncClient):
    """Verify generic 404 for unmapped routes returns uniform error envelope."""
    response = await async_client.get("/api/v1/non-existent-route-xyz")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "request_id" in data["error"]
    assert data["error"]["request_id"] is not None


@pytest.mark.asyncio
async def test_custom_not_found_exception(error_client: httpx.AsyncClient):
    """Verify custom NotFoundError serialization."""
    response = await error_client.get("/test-errors/not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Custom item not found."
    assert data["error"]["details"] == {"item_id": 42}


@pytest.mark.asyncio
async def test_unauthorized_exception(error_client: httpx.AsyncClient):
    """Verify UnauthorizedException returns 401."""
    response = await error_client.get("/test-errors/unauthorized")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_forbidden_exception(error_client: httpx.AsyncClient):
    """Verify ForbiddenException returns 403."""
    response = await error_client.get("/test-errors/forbidden")
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_conflict_exception(error_client: httpx.AsyncClient):
    """Verify ConflictException returns 409."""
    response = await error_client.get("/test-errors/conflict")
    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_service_unavailable_exception(error_client: httpx.AsyncClient):
    """Verify ServiceUnavailableException returns 503."""
    response = await error_client.get("/test-errors/unavailable")
    assert response.status_code == 503
    data = response.json()
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_pydantic_validation_error(error_client: httpx.AsyncClient):
    """Verify request validation errors return 422 with structured details."""
    response = await error_client.post(
        "/test-errors/validation",
        json={"name": "a", "age": -5},  # name too short, age negative
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(data["error"]["details"], list)
    assert len(data["error"]["details"]) >= 2


@pytest.mark.asyncio
async def test_unhandled_exception_hides_stack_trace(error_client: httpx.AsyncClient):
    """Verify unhandled 500 error hides raw internal tracebacks from response."""
    response = await error_client.get("/test-errors/unhandled-500")
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "Simulated unexpected crash" not in data["error"]["message"]
    assert data["error"]["request_id"] is not None
