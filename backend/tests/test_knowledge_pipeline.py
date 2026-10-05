"""
Integration tests for Knowledge Base pipeline, stage tracking, promotion, rollback,
active document deletion protection, and RBAC authorization.
"""

from datetime import datetime, timezone
import io
from pathlib import Path
import pymupdf as fitz
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_access_token, hash_password
from app.infrastructure.db.models.admin import Admin, AdminRole


def _make_valid_pdf_bytes(title: str, text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"{title}\n\n{text}", fontsize=11)
    b = doc.tobytes()
    doc.close()
    return b


@pytest.fixture
async def auth_headers(db_session: AsyncSession) -> dict[str, dict[str, str]]:
    """Create test administrators across all 4 roles and return their auth headers."""
    headers_by_role = {}
    roles = [
        ("super_admin_kb", AdminRole.SUPER_ADMIN),
        ("curator_kb", AdminRole.SITE_CURATOR),
        ("operator_kb", AdminRole.OPERATOR),
        ("viewer_kb", AdminRole.VIEWER),
    ]
    for username, role in roles:
        admin = Admin(
            username=username,
            email=f"{username}@karnataka.gov.in",
            hashed_password=hash_password("KbAdminPass123!"),
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
async def test_knowledge_build_and_promote_pipeline(
    client_with_db: httpx.AsyncClient,
    auth_headers: dict[str, dict[str, str]],
    db_session: AsyncSession,
):
    headers = auth_headers["SUPER_ADMIN"]

    # Step 1: Upload a PDF document
    pdf_content = _make_valid_pdf_bytes(
        title="Pattadakal Temple Complex",
        text="Pattadakal represents the high point of an eclectic art in 7th and 8th centuries under the Chalukya dynasty. Famous temples include Virupaksha Temple, Mallikarjuna Temple, and Sangameshwara Temple.",
    )
    upload_res = await client_with_db.post(
        "/api/v1/admin/documents",
        files={"file": ("pattadakal.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Step 2: Trigger Knowledge Base Build
    build_res = await client_with_db.post(
        "/api/v1/admin/knowledge/generations/build",
        json={"description": "Test Knowledge Base Build for Pattadakal"},
        headers=headers,
    )
    assert build_res.status_code == 201
    gen_data = build_res.json()
    gen_id = gen_data["id"]
    assert gen_data["status"] == "VALIDATED"
    assert gen_data["document_count"] == 1
    assert gen_data["chunk_count"] >= 1
    assert gen_data["embedding_count"] == gen_data["chunk_count"]
    assert gen_data["is_active"] is False
    assert "created_at" in gen_data and gen_data["created_at"] is not None
    assert "generation_version" in gen_data and gen_data["generation_version"].startswith("v_")

    # Step 3: Inspect Generation Detail & Stage History
    detail_res = await client_with_db.get(
        f"/api/v1/admin/knowledge/generations/{gen_id}",
        headers=headers,
    )
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["generation"]["id"] == gen_id
    stages = [s["stage"] for s in detail_data["stages"]]
    assert "INIT" in stages
    assert "EXTRACTION" in stages
    assert "CHUNKING" in stages
    assert "EMBEDDING" in stages
    assert "INDEXING" in stages
    assert "EVALUATION" in stages

    # Step 4: Promote Generation to ACTIVE
    promote_res = await client_with_db.post(
        f"/api/v1/admin/knowledge/generations/{gen_id}/promote",
        headers=headers,
    )
    assert promote_res.status_code == 200
    assert promote_res.json()["is_active"] is True

    # Step 5: Test Active Document Deletion Protection (Expect 409 Conflict)
    delete_doc_res = await client_with_db.delete(
        f"/api/v1/admin/documents/{doc_id}",
        headers=headers,
    )
    assert delete_doc_res.status_code == 409
    assert "referenced by active knowledge generation" in delete_doc_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_knowledge_rollback(
    client_with_db: httpx.AsyncClient,
    auth_headers: dict[str, dict[str, str]],
    db_session: AsyncSession,
):
    headers = auth_headers["SUPER_ADMIN"]

    # Upload doc 1
    pdf1 = _make_valid_pdf_bytes("Belur Temple", "Chennakeshava Temple at Belur is a masterpiece of Hoysala architecture.")
    up1 = await client_with_db.post("/api/v1/admin/documents", files={"file": ("belur.pdf", io.BytesIO(pdf1), "application/pdf")}, headers=headers)
    assert up1.status_code == 201
    doc1_id = up1.json()["id"]

    # Build Gen 1 & Promote
    build1 = await client_with_db.post("/api/v1/admin/knowledge/generations/build", json={"document_ids": [doc1_id]}, headers=headers)
    assert build1.status_code == 201
    gen1_id = build1.json()["id"]
    await client_with_db.post(f"/api/v1/admin/knowledge/generations/{gen1_id}/promote", headers=headers)

    # Upload doc 2
    pdf2 = _make_valid_pdf_bytes("Halebidu Temple", "Hoysaleswara Temple at Halebidu features twin temples dedicated to Lord Shiva.")
    up2 = await client_with_db.post("/api/v1/admin/documents", files={"file": ("halebidu.pdf", io.BytesIO(pdf2), "application/pdf")}, headers=headers)
    assert up2.status_code == 201
    doc2_id = up2.json()["id"]

    # Build Gen 2 & Promote
    build2 = await client_with_db.post("/api/v1/admin/knowledge/generations/build", json={"document_ids": [doc2_id]}, headers=headers)
    assert build2.status_code == 201
    gen2_id = build2.json()["id"]
    await client_with_db.post(f"/api/v1/admin/knowledge/generations/{gen2_id}/promote", headers=headers)

    # Rollback to Gen 1
    rollback_res = await client_with_db.post(f"/api/v1/admin/knowledge/generations/{gen1_id}/rollback", headers=headers)
    assert rollback_res.status_code == 200
    assert rollback_res.json()["is_active"] is True

    # Verify Gen 1 is ACTIVE and Gen 2 is ARCHIVED
    g1_check = await client_with_db.get(f"/api/v1/admin/knowledge/generations/{gen1_id}", headers=headers)
    g2_check = await client_with_db.get(f"/api/v1/admin/knowledge/generations/{gen2_id}", headers=headers)
    assert g1_check.json()["generation"]["is_active"] is True
    assert g1_check.json()["generation"]["status"] == "ACTIVE"
    assert g2_check.json()["generation"]["is_active"] is False
    assert g2_check.json()["generation"]["status"] == "ARCHIVED"


@pytest.mark.asyncio
async def test_knowledge_rbac_enforcement(
    client_with_db: httpx.AsyncClient,
    auth_headers: dict[str, dict[str, str]],
):
    op_headers = auth_headers["OPERATOR"]
    curator_headers = auth_headers["SITE_CURATOR"]

    # Operator cannot build or promote
    build_res = await client_with_db.post(
        "/api/v1/admin/knowledge/generations/build",
        json={},
        headers=op_headers,
    )
    assert build_res.status_code == 403

    # Operator can list
    list_res = await client_with_db.get("/api/v1/admin/knowledge/generations", headers=op_headers)
    assert list_res.status_code == 200

    # Curator can list
    curator_list = await client_with_db.get("/api/v1/admin/knowledge/generations", headers=curator_headers)
    assert curator_list.status_code == 200
