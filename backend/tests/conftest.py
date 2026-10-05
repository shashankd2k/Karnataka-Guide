import os
from typing import AsyncIterator
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure isolated test environment defaults before any module imports settings
os.environ["APP_PROFILE"] = "dev"
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"
os.environ["DB_HOST"] = "127.0.0.1"

from app.core.config import AppProfile, Settings, get_settings
from app.infrastructure.db.models import Base
from app.infrastructure.db.session import get_db_session
from app.main import create_app

# Clear cached settings so test environment variables take effect
get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _mock_db_health_default():
    """Default DB health mock so endpoint health probes pass without requiring live external MySQL."""
    with patch("app.main.check_db_health", new_callable=AsyncMock, return_value=True), \
         patch("app.api.v1.endpoints.health.check_db_health", new_callable=AsyncMock, return_value=True):
        yield


@pytest.fixture
def test_settings() -> Settings:
    """Fixture providing isolated test settings."""
    return Settings(
        PROJECT_NAME="Karnataka Tourism Test Suite",
        VERSION="0.1.0-test",
        API_V1_STR="/api/v1",
        APP_PROFILE=AppProfile.DEV,
        DEBUG=False,
        LOG_LEVEL="DEBUG",
        LOG_JSON=False,

        CORS_ORIGINS=["http://testserver", "http://localhost:5173"],
        JWT_SECRET_KEY="test-super-secret-jwt-key-for-unit-testing-32chars",
        BOOTSTRAP_ADMIN_USERNAME="admin",
        BOOTSTRAP_ADMIN_EMAIL="admin@example.com",
        BOOTSTRAP_ADMIN_PASSWORD="TestPassword123!",
    )


@pytest.fixture
def app(test_settings: Settings):
    """Fixture providing configured FastAPI application instance."""
    return create_app(settings=test_settings)


@pytest.fixture
async def async_client(app, db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    """Fixture providing asynchronous HTTP client with in-memory DB isolation."""
    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_db_session, None)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Fixture providing an isolated in-memory database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client_with_db(app, db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    """Fixture providing HTTP client with get_db_session dependency overridden."""
    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_db_session, None)

