"""
Integration tests for authentication API endpoints (/api/v1/admin/auth/*).
"""

from datetime import datetime, timezone
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password
from app.infrastructure.db.models import Admin, AdminRole


@pytest.fixture
async def active_super_admin(db_session: AsyncSession) -> Admin:
    """Create an active Super Admin in the test database."""
    admin = Admin(
        username="test_super_admin",
        email="superadmin@karnataka.gov.in",
        hashed_password=hash_password("SuperAdminPass2026!"),
        role=AdminRole.SUPER_ADMIN,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.mark.asyncio
async def test_login_endpoint_success(client_with_db: httpx.AsyncClient, active_super_admin: Admin):
    """Verify POST /api/v1/admin/auth/login returns access + refresh tokens."""
    payload = {
        "username": "test_super_admin",
        "password": "SuperAdminPass2026!",
    }
    response = await client_with_db.post("/api/v1/admin/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600


@pytest.mark.asyncio
async def test_login_endpoint_invalid_credentials(client_with_db: httpx.AsyncClient, active_super_admin: Admin):
    """Verify POST /api/v1/admin/auth/login returns 401 with generic error envelope."""
    payload = {
        "username": "test_super_admin",
        "password": "WrongPassword!",
    }
    response = await client_with_db.post("/api/v1/admin/auth/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert data["error"]["message"] == "Invalid username or password."


@pytest.mark.asyncio
async def test_refresh_endpoint_and_rotation(client_with_db: httpx.AsyncClient, active_super_admin: Admin):
    """Verify POST /api/v1/admin/auth/refresh rotates token and prevents reuse."""
    # 1. Login
    login_res = await client_with_db.post(
        "/api/v1/admin/auth/login",
        json={"username": "test_super_admin", "password": "SuperAdminPass2026!"},
    )
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]

    # 2. Refresh token
    refresh_res = await client_with_db.post(
        "/api/v1/admin/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert new_tokens["access_token"] is not None
    assert new_tokens["refresh_token"] != refresh_token

    # 3. Attempt reuse of old refresh token: Must return 401
    reuse_res = await client_with_db.post(
        "/api/v1/admin/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reuse_res.status_code == 401
    assert reuse_res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_logout_endpoint(client_with_db: httpx.AsyncClient, active_super_admin: Admin):
    """Verify POST /api/v1/admin/auth/logout revokes refresh token."""
    login_res = await client_with_db.post(
        "/api/v1/admin/auth/login",
        json={"username": "test_super_admin", "password": "SuperAdminPass2026!"},
    )
    tokens = login_res.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    logout_res = await client_with_db.post(
        "/api/v1/admin/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Successfully logged out."


@pytest.mark.asyncio
async def test_me_endpoint_success_and_protection(client_with_db: httpx.AsyncClient, active_super_admin: Admin):
    """Verify GET /api/v1/admin/auth/me returns admin data and rejects unauthenticated requests."""
    # 1. Unauthenticated request -> 401
    unauth_res = await client_with_db.get("/api/v1/admin/auth/me")
    assert unauth_res.status_code == 401

    # 2. Authenticated request -> 200 with safe data (no password hash)
    login_res = await client_with_db.post(
        "/api/v1/admin/auth/login",
        json={"username": "test_super_admin", "password": "SuperAdminPass2026!"},
    )
    access_token = login_res.json()["access_token"]

    me_res = await client_with_db.get(
        "/api/v1/admin/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == "test_super_admin"
    assert me_data["role"] == "SUPER_ADMIN"
    assert me_data["is_active"] is True
    assert "hashed_password" not in me_data
    assert "password" not in me_data
