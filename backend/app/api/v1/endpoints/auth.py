"""
Administrative authentication and authorization endpoints (/api/v1/admin/auth).
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.auth.dependencies import get_current_admin, require_role
from app.application.auth.schemas import (
    AdminResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)
from app.application.auth.service import (
    authenticate_admin,
    refresh_admin_token,
    revoke_admin_token,
)
from app.core.config import AppProfile, get_settings
from app.core.errors import NotFoundException
from app.infrastructure.db.models.admin import Admin, AdminRole
from app.infrastructure.db.session import get_db_session

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Login",
    description="Authenticate admin credentials and obtain JWT access + refresh tokens.",
)
async def login(
    req: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Authenticate administrator and return access and refresh tokens."""
    settings = get_settings()
    client_ip = request.client.host if request.client else None
    admin, access_token, refresh_token = await authenticate_admin(
        session=session,
        username_or_email=req.username,
        password=req.password,
        ip_address=client_ip,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Rotate refresh token, invalidate previous token, and issue a fresh token pair.",
)
async def refresh(
    req: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Rotate refresh token and issue new access and refresh tokens."""
    settings = get_settings()
    client_ip = request.client.host if request.client else None
    admin, access_token, refresh_token = await refresh_admin_token(
        session=session,
        refresh_token_str=req.refresh_token,
        ip_address=client_ip,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Admin Logout",
    description="Revoke session tokens and record security audit log.",
)
async def logout(
    req: LogoutRequest,
    request: Request,
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Revoke admin tokens and record logout event."""
    client_ip = request.client.host if request.client else None
    await revoke_admin_token(
        session=session,
        admin_id=current_admin.id,
        refresh_token_str=req.refresh_token,
        ip_address=client_ip,
    )
    return {"message": "Successfully logged out."}


@router.get(
    "/me",
    response_model=AdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Current Admin Profile",
    description="Retrieve profile details for currently authenticated admin.",
)
async def get_me(
    current_admin: Admin = Depends(get_current_admin),
) -> AdminResponse:
    """Return safe administrator details."""
    return AdminResponse.model_validate(current_admin)


# ---------------------------------------------------------------------------
# Protected RBAC Route Demonstrators (Restricted to DEV Profile)
# ---------------------------------------------------------------------------


def _ensure_dev_profile():
    if get_settings().APP_PROFILE != AppProfile.DEV:
        raise NotFoundException("Resource not found.")


@router.get(
    "/test/super-admin",
    status_code=status.HTTP_200_OK,
    summary="Super Admin Only (Dev only)",
    include_in_schema=False,
)
async def test_super_admin_only(
    admin: Admin = Depends(require_role(AdminRole.SUPER_ADMIN)),
) -> dict:
    _ensure_dev_profile()
    return {"message": "Super Admin access granted", "admin": admin.username}


@router.get(
    "/test/curator",
    status_code=status.HTTP_200_OK,
    summary="Site Curator Allowed (Dev only)",
    include_in_schema=False,
)
async def test_curator_allowed(
    admin: Admin = Depends(require_role(AdminRole.SITE_CURATOR)),
) -> dict:
    _ensure_dev_profile()
    return {"message": "Curator access granted", "admin": admin.username}


@router.get(
    "/test/operator",
    status_code=status.HTTP_200_OK,
    summary="Operator Allowed (Dev only)",
    include_in_schema=False,
)
async def test_operator_allowed(
    admin: Admin = Depends(require_role(AdminRole.OPERATOR)),
) -> dict:
    _ensure_dev_profile()
    return {"message": "Operator access granted", "admin": admin.username}


@router.get(
    "/test/viewer",
    status_code=status.HTTP_200_OK,
    summary="Viewer Allowed (Dev only)",
    include_in_schema=False,
)
async def test_viewer_allowed(
    admin: Admin = Depends(require_role(AdminRole.VIEWER)),
) -> dict:
    _ensure_dev_profile()
    return {"message": "Viewer access granted", "admin": admin.username}
