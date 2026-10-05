"""
Integration tests for administrative document management endpoints (/api/v1/admin/documents/*).
"""

from datetime import datetime, timezone
import io
from pathlib import Path
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.infrastructure.db.models import Admin, AdminRole, AuditLog, Document

SAMPLE_PDF_BYTES_1 = b"%PDF-1.4\n1 0 obj\n<<\n/Title (Hampi Heritage Guide)\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
SAMPLE_PDF_BYTES_2 = b"%PDF-1.4\n1 0 obj\n<<\n/Title (Mysore Palace Guide)\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"


@pytest.fixture
async def auth_headers(db_session: AsyncSession) -> dict[str, dict[str, str]]:
    """Create test administrators across all 4 roles and return their auth headers."""
    headers_by_role = {}
    roles = [
        ("super_admin_doc", AdminRole.SUPER_ADMIN),
        ("curator_doc", AdminRole.SITE_CURATOR),
        ("operator_doc", AdminRole.OPERATOR),
        ("viewer_doc", AdminRole.VIEWER),
    ]
    for username, role in roles:
        admin = Admin(
            username=username,
            email=f"{username}@karnataka.gov.in",
            hashed_password=hash_password("DocAdminPass123!"),
            role=role,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(admin)
        await db_session.commit()
        await db_session.refresh(admin)

        token = create_access_token(admin_id=admin.id, role=role.value)
        headers_by_role[role.value] = {"Authorization": f"Bearer {token}"}

    return headers_by_role


@pytest.mark.asyncio
async def test_upload_document_super_admin_success(
    client_with_db: httpx.AsyncClient,
    auth_headers: dict[str, dict[str, str]],
    db_session: AsyncSession,
):
    """Verify SUPER_ADMIN can upload a valid PDF document."""
    files = {"file": ("Hampi_Heritage.pdf", io.BytesIO(SAMPLE_PDF_BYTES_1), "application/pdf")}
    res = await client_with_db.post(
        "/api/v1/admin/documents",
        files=files,
        headers=auth_headers["SUPER_ADMIN"],
    )
    assert res.status_code == 201
    data = res.json()
    assert data["original_name"] == "Hampi_Heritage.pdf"
    assert data["file_size_bytes"] == len(SAMPLE_PDF_BYTES_1)
    assert data["status"] == "UPLOADED"
    assert "id" in data

    # Verify physical file existence in storage
    settings = get_settings()
    physical_path = settings.resolved_storage_path / data["filename"]
    assert physical_path.exists()
    assert physical_path.read_bytes() == SAMPLE_PDF_BYTES_1

    # Cleanup physical file
    physical_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_upload_document_curator_success(
    client_with_db: httpx.AsyncClient,
    auth_headers: dict[str, dict[str, str]],
):
    """Verify SITE_CURATOR can upload a valid PDF document."""
    files = {"file": ("Mysore_Palace.pdf", io.BytesIO(SAMPLE_PDF_BYTES_2), "application/pdf")}
    res = await client_with_db.post(
        "/api/v1/admin/documents",
        files=files,
        headers=auth_headers["SITE_CURATOR"],
    )
    assert res.status_code == 201
    data = res.json()
    assert data["original_name"] == "Mysore_Palace.pdf"

    # Cleanup
    settings = get_settings()
    (settings.resolved_storage_path / data["filename"]).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_upload_document_rbac_denial(
    client_with_db: httpx.AsyncClient,
    auth_headers: dict[str, dict[str, str]],
):
    """Verify OPERATOR and VIEWER are forbidden from uploading documents."""
    for role in ["OPERATOR", "VIEWER"]:
        files = {"file": ("Test.pdf", io.BytesIO(SAMPLE_PDF_BYTES_1), "application/pdf")}
        res = await client_with_db.post(
            "/api/v1/admin/documents",
            files=files,
            headers=auth_headers[role],
        )
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_upload_document_duplicate_conflict(
    client_with_db: httpx.AsyncClient,
    auth_headers: dict[str, dict[str, str]],
):
    """Verify uploading duplicate PDF content returns 409 Conflict."""
    files1 = {"file": ("Hampi_v1.pdf", io.BytesIO(SAMPLE_PDF_BYTES_1), "application/pdf")}
    res1 = await client_with_db.post(
        "/api/v1/admin/documents",
        files=files1,
        headers=auth_headers["SUPER_ADMIN"],
    )
    assert res1.status_code == 201
    doc1 = res1.json()

    # Attempt duplicate upload with same content
    files2 = {"file": ("Hampi_Duplicate.pdf", io.BytesIO(SAMPLE_PDF_BYTES_1), "application/pdf")}
    res2 = await client_with_db.post(
        "/api/v1/admin/documents",
        files=files2,
        headers=auth_headers["SUPER_ADMIN"],
    )
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "CONFLICT"

    # Cleanup
    settings = get_settings()
    (settings.resolved_storage_path / doc1["filename"]).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_list_and_paginate_documents(
    client_with_db: httpx.AsyncClient,
    auth_headers: dict[str, dict[str, str]],
):
    """Verify document listing and pagination."""
    # Upload 2 docs
    files1 = {"file": ("Doc1.pdf", io.BytesIO(SAMPLE_PDF_BYTES_1), "application/pdf")}
    files2 = {"file": ("Doc2.pdf", io.BytesIO(SAMPLE_PDF_BYTES_2), "application/pdf")}
    res1 = await client_with_db.post("/api/v1/admin/documents", files=files1, headers=auth_headers["SUPER_ADMIN"])
    res2 = await client_with_db.post("/api/v1/admin/documents", files=files2, headers=auth_headers["SUPER_ADMIN"])
    assert res1.status_code == 201
    assert res2.status_code == 201

    # List with VIEWER role
    res_list = await client_with_db.get(
        "/api/v1/admin/documents?skip=0&limit=10",
        headers=auth_headers["VIEWER"],
    )
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] >= 2
    assert len(list_data["items"]) >= 2

    # Cleanup
    settings = get_settings()
    (settings.resolved_storage_path / res1.json()["filename"]).unlink(missing_ok=True)
    (settings.resolved_storage_path / res2.json()["filename"]).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_get_document_metadata_and_download(
    client_with_db: httpx.AsyncClient,
    auth_headers: dict[str, dict[str, str]],
):
    """Verify metadata retrieval and PDF download matching original bytes."""
    files = {"file": ("DownloadTest.pdf", io.BytesIO(SAMPLE_PDF_BYTES_1), "application/pdf")}
    upload_res = await client_with_db.post(
        "/api/v1/admin/documents",
        files=files,
        headers=auth_headers["SUPER_ADMIN"],
    )
    doc_id = upload_res.json()["id"]

    # 1. Get metadata
    meta_res = await client_with_db.get(
        f"/api/v1/admin/documents/{doc_id}",
        headers=auth_headers["OPERATOR"],
    )
    assert meta_res.status_code == 200
    assert meta_res.json()["original_name"] == "DownloadTest.pdf"

    # 2. Download
    down_res = await client_with_db.get(
        f"/api/v1/admin/documents/{doc_id}/download",
        headers=auth_headers["VIEWER"],
    )
    assert down_res.status_code == 200
    assert down_res.content == SAMPLE_PDF_BYTES_1

    # Cleanup
    settings = get_settings()
    (settings.resolved_storage_path / upload_res.json()["filename"]).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_delete_document(
    client_with_db: httpx.AsyncClient,
    auth_headers: dict[str, dict[str, str]],
    db_session: AsyncSession,
):
    """Verify document deletion removes DB record and physical file."""
    files = {"file": ("DeleteMe.pdf", io.BytesIO(SAMPLE_PDF_BYTES_1), "application/pdf")}
    upload_res = await client_with_db.post(
        "/api/v1/admin/documents",
        files=files,
        headers=auth_headers["SUPER_ADMIN"],
    )
    doc_id = upload_res.json()["id"]
    filename = upload_res.json()["filename"]

    settings = get_settings()
    physical_path = settings.resolved_storage_path / filename
    assert physical_path.exists()

    # OPERATOR cannot delete -> 403
    del_op = await client_with_db.delete(
        f"/api/v1/admin/documents/{doc_id}",
        headers=auth_headers["OPERATOR"],
    )
    assert del_op.status_code == 403

    # SITE_CURATOR can delete -> 200
    del_cur = await client_with_db.delete(
        f"/api/v1/admin/documents/{doc_id}",
        headers=auth_headers["SITE_CURATOR"],
    )
    assert del_cur.status_code == 200

    # Verify physical file unlinked
    assert not physical_path.exists()

    # Verify DB record deleted
    get_res = await client_with_db.get(
        f"/api/v1/admin/documents/{doc_id}",
        headers=auth_headers["SUPER_ADMIN"],
    )
    assert get_res.status_code == 404
