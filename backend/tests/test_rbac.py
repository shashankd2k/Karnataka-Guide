"""
Role-Based Access Control (RBAC) authorization unit and endpoint tests.
"""

from datetime import datetime, timezone
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_access_token, hash_password
from app.infrastructure.db.models import Admin, AdminRole


@pytest.fixture
async def role_users(db_session: AsyncSession) -> dict[str, Admin]:
    """Create test admin users with different roles."""
    users = {}
    roles = [
        ("super_admin_user", AdminRole.SUPER_ADMIN),
        ("curator_user", AdminRole.SITE_CURATOR),
        ("operator_user", AdminRole.OPERATOR),
        ("viewer_user", AdminRole.VIEWER),
    ]
    for username, role in roles:
        admin = Admin(
            username=username,
            email=f"{username}@karnataka.gov.in",
            hashed_password=hash_password("RolePass123!"),
            role=role,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(admin)
        users[role.value] = admin

    await db_session.commit()
    for u in users.values():
        await db_session.refresh(u)
    return users


@pytest.mark.asyncio
async def test_super_admin_has_full_access(client_with_db: httpx.AsyncClient, role_users: dict[str, Admin]):
    """Verify SUPER_ADMIN can access all role-protected endpoints."""
    super_admin = role_users["SUPER_ADMIN"]
    token = create_access_token(admin_id=super_admin.id, role="SUPER_ADMIN")
    headers = {"Authorization": f"Bearer {token}"}

    for path in ["super-admin", "curator", "operator", "viewer"]:
        res = await client_with_db.get(f"/api/v1/admin/auth/test/{path}", headers=headers)
        assert res.status_code == 200, f"SUPER_ADMIN failed on /test/{path}"


@pytest.mark.asyncio
async def test_site_curator_role_enforcement(client_with_db: httpx.AsyncClient, role_users: dict[str, Admin]):
    """Verify SITE_CURATOR can access curator route but is forbidden on super-admin and operator routes."""
    curator = role_users["SITE_CURATOR"]
    token = create_access_token(admin_id=curator.id, role="SITE_CURATOR")
    headers = {"Authorization": f"Bearer {token}"}

    # Allowed
    res_curator = await client_with_db.get("/api/v1/admin/auth/test/curator", headers=headers)
    assert res_curator.status_code == 200

    # Forbidden on super-admin
    res_super = await client_with_db.get("/api/v1/admin/auth/test/super-admin", headers=headers)
    assert res_super.status_code == 403
    assert res_super.json()["error"]["code"] == "FORBIDDEN"

    # Forbidden on operator
    res_op = await client_with_db.get("/api/v1/admin/auth/test/operator", headers=headers)
    assert res_op.status_code == 403


@pytest.mark.asyncio
async def test_operator_role_enforcement(client_with_db: httpx.AsyncClient, role_users: dict[str, Admin]):
    """Verify OPERATOR can access operator route but is forbidden on curator route."""
    operator = role_users["OPERATOR"]
    token = create_access_token(admin_id=operator.id, role="OPERATOR")
    headers = {"Authorization": f"Bearer {token}"}

    # Allowed
    res_op = await client_with_db.get("/api/v1/admin/auth/test/operator", headers=headers)
    assert res_op.status_code == 200

    # Forbidden on curator
    res_cur = await client_with_db.get("/api/v1/admin/auth/test/curator", headers=headers)
    assert res_cur.status_code == 403


@pytest.mark.asyncio
async def test_viewer_role_enforcement(client_with_db: httpx.AsyncClient, role_users: dict[str, Admin]):
    """Verify VIEWER can access viewer route but is forbidden on operator and curator routes."""
    viewer = role_users["VIEWER"]
    token = create_access_token(admin_id=viewer.id, role="VIEWER")
    headers = {"Authorization": f"Bearer {token}"}

    # Allowed
    res_viewer = await client_with_db.get("/api/v1/admin/auth/test/viewer", headers=headers)
    assert res_viewer.status_code == 200

    # Forbidden on operator
    res_op = await client_with_db.get("/api/v1/admin/auth/test/operator", headers=headers)
    assert res_op.status_code == 403
