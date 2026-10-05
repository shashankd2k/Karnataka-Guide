"""
Unit tests for explicit super admin bootstrap utility.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings
from app.core.security import verify_password
from app.infrastructure.db.bootstrap_admin import bootstrap_super_admin
from app.infrastructure.db.models import Admin, AdminRole


@pytest.mark.asyncio
async def test_bootstrap_super_admin_creates_account(db_session: AsyncSession):
    """Verify bootstrap creates a new super admin account with Argon2id hash."""
    settings = Settings(
        JWT_SECRET_KEY="test-secret-key-for-bootstrap-testing-32chars",
        BOOTSTRAP_ADMIN_USERNAME="karnataka_root",
        BOOTSTRAP_ADMIN_EMAIL="root@karnataka.gov.in",
        BOOTSTRAP_ADMIN_PASSWORD="RootSuperPassword2026!",
    )
    admin = await bootstrap_super_admin(session=db_session, settings=settings)
    assert admin is not None
    assert admin.username == "karnataka_root"
    assert admin.email == "root@karnataka.gov.in"
    assert admin.role == AdminRole.SUPER_ADMIN
    assert admin.is_active is True
    assert admin.hashed_password.startswith("$argon2id$")
    assert verify_password("RootSuperPassword2026!", admin.hashed_password) is True


@pytest.mark.asyncio
async def test_bootstrap_super_admin_is_idempotent(db_session: AsyncSession):
    """Verify running bootstrap multiple times does not duplicate admin."""
    settings = Settings(
        JWT_SECRET_KEY="test-secret-key-for-bootstrap-testing-32chars",
        BOOTSTRAP_ADMIN_USERNAME="karnataka_root",
        BOOTSTRAP_ADMIN_EMAIL="root@karnataka.gov.in",
        BOOTSTRAP_ADMIN_PASSWORD="RootSuperPassword2026!",
    )
    admin1 = await bootstrap_super_admin(session=db_session, settings=settings)
    admin2 = await bootstrap_super_admin(session=db_session, settings=settings)
    assert admin1.id == admin2.id


@pytest.mark.asyncio
async def test_bootstrap_super_admin_skipped_when_password_missing(db_session: AsyncSession):
    """Verify bootstrap is skipped gracefully when BOOTSTRAP_ADMIN_PASSWORD is empty or CHANGE_ME."""
    settings_empty = Settings(
        JWT_SECRET_KEY="test-secret-key-for-bootstrap-testing-32chars",
        BOOTSTRAP_ADMIN_PASSWORD="",
    )
    admin_none = await bootstrap_super_admin(session=db_session, settings=settings_empty)
    assert admin_none is None

    settings_placeholder = Settings(
        JWT_SECRET_KEY="test-secret-key-for-bootstrap-testing-32chars",
        BOOTSTRAP_ADMIN_PASSWORD="CHANGE_ME",
    )
    admin_placeholder = await bootstrap_super_admin(session=db_session, settings=settings_placeholder)
    assert admin_placeholder is None
