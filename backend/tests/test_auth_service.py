"""
Unit tests for authentication service layer, token rotation, reuse detection, and security audit logs.
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.auth.service import (
    authenticate_admin,
    refresh_admin_token,
    revoke_admin_token,
)
from app.core.errors import UnauthorizedException
from app.core.security import hash_password
from app.infrastructure.db.models import Admin, AdminRole, AuditLog


@pytest.fixture
async def sample_admin(db_session: AsyncSession) -> Admin:
    """Create a sample active admin in the test session."""
    admin = Admin(
        username="karnataka_curator",
        email="curator@karnataka.gov.in",
        hashed_password=hash_password("Curator@Pass123"),
        role=AdminRole.SITE_CURATOR,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def inactive_admin(db_session: AsyncSession) -> Admin:
    """Create a disabled admin in the test session."""
    admin = Admin(
        username="disabled_admin",
        email="disabled@karnataka.gov.in",
        hashed_password=hash_password("Disabled@Pass123"),
        role=AdminRole.OPERATOR,
        is_active=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.mark.asyncio
async def test_authenticate_admin_success(db_session: AsyncSession, sample_admin: Admin):
    """Verify successful authentication returns valid tokens and records audit log."""
    admin, access_token, refresh_token = await authenticate_admin(
        session=db_session,
        username_or_email="karnataka_curator",
        password="Curator@Pass123",
        ip_address="127.0.0.1",
    )
    assert admin.id == sample_admin.id
    assert access_token is not None
    assert refresh_token is not None

    # Check audit log
    logs = (await db_session.execute(select(AuditLog).where(AuditLog.action == "AUTH_LOGIN_SUCCESS"))).scalars().all()
    assert len(logs) == 1
    assert logs[0].admin_id == sample_admin.id


@pytest.mark.asyncio
async def test_authenticate_admin_invalid_username(db_session: AsyncSession):
    """Verify generic failure message when username does not exist."""
    with pytest.raises(UnauthorizedException) as exc_info:
        await authenticate_admin(
            session=db_session,
            username_or_email="nonexistent_user",
            password="SomePassword123",
            ip_address="127.0.0.1",
        )
    assert exc_info.value.message == "Invalid username or password."


@pytest.mark.asyncio
async def test_authenticate_admin_invalid_password(db_session: AsyncSession, sample_admin: Admin):
    """Verify generic failure message on wrong password and failure audit logged."""
    with pytest.raises(UnauthorizedException) as exc_info:
        await authenticate_admin(
            session=db_session,
            username_or_email="karnataka_curator",
            password="WrongPassword999",
            ip_address="127.0.0.1",
        )
    assert exc_info.value.message == "Invalid username or password."

    logs = (await db_session.execute(select(AuditLog).where(AuditLog.action == "AUTH_LOGIN_FAILED"))).scalars().all()
    assert len(logs) == 1


@pytest.mark.asyncio
async def test_authenticate_admin_inactive_rejected(db_session: AsyncSession, inactive_admin: Admin):
    """Verify disabled admin account is rejected."""
    with pytest.raises(UnauthorizedException) as exc_info:
        await authenticate_admin(
            session=db_session,
            username_or_email="disabled_admin",
            password="Disabled@Pass123",
            ip_address="127.0.0.1",
        )
    assert "disabled" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_refresh_rotation_and_reuse_rejection(db_session: AsyncSession, sample_admin: Admin):
    """Verify refresh rotation invalidates the old token and detects token reuse."""
    _, _, initial_refresh_token = await authenticate_admin(
        session=db_session,
        username_or_email="karnataka_curator",
        password="Curator@Pass123",
    )

    # First refresh: Success
    admin, new_access, new_refresh = await refresh_admin_token(
        session=db_session,
        refresh_token_str=initial_refresh_token,
        ip_address="127.0.0.1",
    )
    assert admin.id == sample_admin.id
    assert new_access is not None
    assert new_refresh is not None
    assert new_refresh != initial_refresh_token

    # Replay/Reuse attempt with initial_refresh_token: Must fail!
    with pytest.raises(UnauthorizedException) as exc_info:
        await refresh_admin_token(
            session=db_session,
            refresh_token_str=initial_refresh_token,
            ip_address="127.0.0.1",
        )
    assert "already been used" in exc_info.value.message.lower()

    # Verify reuse detection audit event logged
    reuse_logs = (await db_session.execute(select(AuditLog).where(AuditLog.action == "AUTH_TOKEN_REUSE_DETECTED"))).scalars().all()
    assert len(reuse_logs) == 1


@pytest.mark.asyncio
async def test_revoke_admin_token_on_logout(db_session: AsyncSession, sample_admin: Admin):
    """Verify logout revokes the refresh token and records audit log."""
    _, _, refresh_token = await authenticate_admin(
        session=db_session,
        username_or_email="karnataka_curator",
        password="Curator@Pass123",
    )

    await revoke_admin_token(
        session=db_session,
        admin_id=sample_admin.id,
        refresh_token_str=refresh_token,
        ip_address="127.0.0.1",
    )

    # Attempt to use revoked refresh token: Must fail!
    with pytest.raises(UnauthorizedException):
        await refresh_admin_token(
            session=db_session,
            refresh_token_str=refresh_token,
        )
