"""
Authentication and Role-Based Access Control (RBAC) dependencies.
"""

from typing import Callable, Optional, Sequence
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.infrastructure.db.models.admin import Admin, AdminRole
from app.infrastructure.db.session import get_db_session

# Standard Bearer auth header extractor
oauth2_scheme = HTTPBearer(auto_error=False)


async def get_current_admin(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> Admin:
    """Extract and validate JWT access token from request authorization header."""
    if not credentials or not credentials.credentials:
        raise UnauthorizedException("Authentication credentials are required.")

    token = credentials.credentials
    payload = decode_token(token, expected_type="access")
    admin_id = payload.get("sub")
    if not admin_id:
        raise UnauthorizedException("Invalid token subject.")

    admin = await session.get(Admin, admin_id)
    if not admin:
        raise UnauthorizedException("Admin account not found.")

    if not admin.is_active:
        raise UnauthorizedException("Admin account is disabled.")

    return admin


def require_role(*allowed_roles: AdminRole) -> Callable[[Admin], Admin]:
    """
    Role-Based Access Control (RBAC) dependency factory.
    Enforces that current admin has at least one of the specified roles.
    SUPER_ADMIN always has full access to all protected resources.
    """
    async def role_checker(current_admin: Admin = Depends(get_current_admin)) -> Admin:
        if current_admin.role == AdminRole.SUPER_ADMIN:
            return current_admin

        if current_admin.role in allowed_roles:
            return current_admin

        raise ForbiddenException(
            f"Insufficient permissions. Required role: {[r.value for r in allowed_roles]}."
        )

    return role_checker
