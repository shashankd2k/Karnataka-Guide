"""
Explicit and idempotent Super Administrator bootstrap utility.
Must be invoked explicitly via CLI or administrative scripts, not silently on every startup.
"""

import asyncio
from datetime import datetime, timezone
import sys
from typing import Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.infrastructure.db.models.admin import Admin, AdminRole
from app.infrastructure.db.session import close_db_engine, get_session_factory

logger = structlog.get_logger(__name__)


async def bootstrap_super_admin(
    session: AsyncSession,
    settings: Optional[Settings] = None,
) -> Optional[Admin]:
    """
    Explicitly bootstrap initial SUPER_ADMIN account idempotently.
    Returns Admin instance if created or existing, None if bootstrap password not configured.
    """
    if settings is None:
        settings = get_settings()

    username = settings.BOOTSTRAP_ADMIN_USERNAME.strip()
    email = settings.BOOTSTRAP_ADMIN_EMAIL.strip().lower()
    plain_password = settings.BOOTSTRAP_ADMIN_PASSWORD

    if not plain_password or plain_password == "CHANGE_ME":
        logger.warning(
            "bootstrap_admin_skipped_missing_password",
            detail="BOOTSTRAP_ADMIN_PASSWORD environment variable is not configured or set to placeholder.",
        )
        return None

    # Check if super admin or matching user already exists
    stmt = select(Admin).where(
        or_(
            Admin.username == username,
            Admin.email == email,
        )
    )
    existing_admin = (await session.execute(stmt)).scalar_one_or_none()
    if existing_admin:
        logger.info(
            "bootstrap_admin_already_exists",
            admin_id=existing_admin.id,
            username=existing_admin.username,
            role=existing_admin.role.value,
        )
        return existing_admin

    # Hash with Argon2id and create super admin
    hashed = hash_password(plain_password)
    admin = Admin(
        username=username,
        email=email,
        hashed_password=hashed,
        role=AdminRole.SUPER_ADMIN,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)

    logger.info(
        "bootstrap_admin_created_successfully",
        admin_id=admin.id,
        username=admin.username,
        email=admin.email,
        role=admin.role.value,
    )
    return admin


async def main() -> None:
    """CLI entrypoint for explicit bootstrap execution."""
    factory = get_session_factory()
    try:
        async with factory() as session:
            admin = await bootstrap_super_admin(session)
            if admin:
                print(f"SUPER_ADMIN ready: username='{admin.username}', email='{admin.email}', role='{admin.role.value}'")
            else:
                print("Bootstrap aborted: please configure BOOTSTRAP_ADMIN_PASSWORD in environment.")
                sys.exit(1)
    finally:
        await close_db_engine()


if __name__ == "__main__":
    asyncio.run(main())
