"""
Authentication service layer: admin verification, token rotation, revocation, and security audit logging.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from app.core.config import get_settings
from app.core.errors import UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.infrastructure.db.models import Admin, AuditLog

logger = structlog.get_logger(__name__)


async def record_audit_event(
    session: AsyncSession,
    action: str,
    resource_type: str = "AUTH",
    admin_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Record a security audit log event."""
    log_entry = AuditLog(
        admin_id=admin_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details_json=json.dumps(details) if details else None,
        ip_address=ip_address,
        created_at=datetime.now(timezone.utc),
    )
    session.add(log_entry)
    await session.flush()
    return log_entry


async def authenticate_admin(
    session: AsyncSession,
    username_or_email: str,
    password: str,
    ip_address: Optional[str] = None,
) -> Tuple[Admin, str, str]:
    """
    Authenticate administrator credentials with Argon2id constant-time verification.
    Returns (Admin, access_token, refresh_token).
    """
    stmt = select(Admin).where(
        or_(
            Admin.username == username_or_email.strip(),
            Admin.email == username_or_email.strip().lower(),
        )
    )
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    # Generic authentication failure to prevent user enumeration
    if not admin:
        logger.warning("auth_login_failed_user_not_found", username=username_or_email, ip=ip_address)
        await record_audit_event(
            session=session,
            action="AUTH_LOGIN_FAILED",
            resource_type="AUTH",
            resource_id=username_or_email[:100],
            details={"reason": "user_not_found"},
            ip_address=ip_address,
        )
        await session.commit()
        raise UnauthorizedException("Invalid username or password.")

    if not admin.is_active:
        logger.warning("auth_login_failed_inactive_account", admin_id=admin.id, ip=ip_address)
        await record_audit_event(
            session=session,
            admin_id=admin.id,
            action="AUTH_LOGIN_FAILED",
            resource_type="AUTH",
            resource_id=admin.id,
            details={"reason": "account_inactive"},
            ip_address=ip_address,
        )
        await session.commit()
        raise UnauthorizedException("Account is disabled. Please contact the system administrator.")

    if not verify_password(password, admin.hashed_password):
        logger.warning("auth_login_failed_invalid_password", admin_id=admin.id, ip=ip_address)
        await record_audit_event(
            session=session,
            admin_id=admin.id,
            action="AUTH_LOGIN_FAILED",
            resource_type="AUTH",
            resource_id=admin.id,
            details={"reason": "invalid_password"},
            ip_address=ip_address,
        )
        await session.commit()
        raise UnauthorizedException("Invalid username or password.")

    # Successful authentication
    admin.last_login_at = datetime.now(timezone.utc)
    session.add(admin)

    access_token = create_access_token(admin_id=admin.id, role=admin.role.value)
    refresh_token, jti = create_refresh_token(admin_id=admin.id, role=admin.role.value)

    await record_audit_event(
        session=session,
        admin_id=admin.id,
        action="AUTH_LOGIN_SUCCESS",
        resource_type="ADMIN",
        resource_id=admin.id,
        details={"role": admin.role.value, "initial_jti": jti},
        ip_address=ip_address,
    )

    logger.info("auth_login_success", admin_id=admin.id, role=admin.role.value)
    return admin, access_token, refresh_token


async def refresh_admin_token(
    session: AsyncSession,
    refresh_token_str: str,
    ip_address: Optional[str] = None,
) -> Tuple[Admin, str, str]:
    """
    Validate refresh token, check for reuse, rotate token, and issue a new pair.
    Returns (Admin, new_access_token, new_refresh_token).
    """
    payload = decode_token(refresh_token_str, expected_type="refresh")
    admin_id = payload["sub"]
    jti = payload["jti"]

    # Check if this JTI was already rotated or revoked (Reuse Detection)
    stmt = select(AuditLog).where(
        AuditLog.resource_type == "REFRESH_TOKEN",
        AuditLog.resource_id == jti,
        AuditLog.action.in_(["AUTH_REFRESH_ROTATED", "AUTH_REFRESH_REVOKED"]),
    )
    existing_revocation = (await session.execute(stmt)).scalar_one_or_none()
    if existing_revocation:
        logger.error(
            "auth_refresh_token_reuse_detected",
            admin_id=admin_id,
            jti=jti,
            ip=ip_address,
        )
        await record_audit_event(
            session=session,
            admin_id=admin_id,
            action="AUTH_TOKEN_REUSE_DETECTED",
            resource_type="REFRESH_TOKEN",
            resource_id=jti,
            details={"revocation_action": existing_revocation.action},
            ip_address=ip_address,
        )
        await session.commit()
        raise UnauthorizedException("Refresh token is invalid or has already been used.")

    # Validate admin account status
    admin = await session.get(Admin, admin_id)
    if not admin or not admin.is_active:
        logger.warning("auth_refresh_failed_inactive_or_deleted", admin_id=admin_id)
        raise UnauthorizedException("Account is disabled or does not exist.")

    # Mark old JTI as rotated in audit log
    await record_audit_event(
        session=session,
        admin_id=admin.id,
        action="AUTH_REFRESH_ROTATED",
        resource_type="REFRESH_TOKEN",
        resource_id=jti,
        details={"rotated_at": datetime.now(timezone.utc).isoformat()},
        ip_address=ip_address,
    )

    # Issue new pair with new JTI
    new_access_token = create_access_token(admin_id=admin.id, role=admin.role.value)
    new_refresh_token, new_jti = create_refresh_token(admin_id=admin.id, role=admin.role.value)

    logger.info("auth_refresh_token_rotated", admin_id=admin.id, old_jti=jti, new_jti=new_jti)
    return admin, new_access_token, new_refresh_token


async def revoke_admin_token(
    session: AsyncSession,
    admin_id: str,
    refresh_token_str: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Revoke refresh token and record logout event."""
    if refresh_token_str:
        try:
            payload = decode_token(refresh_token_str, expected_type="refresh")
            jti = payload.get("jti")
            if jti:
                await record_audit_event(
                    session=session,
                    admin_id=admin_id,
                    action="AUTH_REFRESH_REVOKED",
                    resource_type="REFRESH_TOKEN",
                    resource_id=jti,
                    ip_address=ip_address,
                )
        except Exception:
            # If token already invalid/expired, still proceed with logout audit
            pass

    await record_audit_event(
        session=session,
        admin_id=admin_id,
        action="AUTH_LOGOUT",
        resource_type="ADMIN",
        resource_id=admin_id,
        ip_address=ip_address,
    )
    logger.info("auth_logout_success", admin_id=admin_id)
