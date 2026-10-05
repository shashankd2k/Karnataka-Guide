"""
Integration tests for Admin RAG retrieval diagnostic endpoints.
"""

from datetime import datetime, timezone
import io
import pymupdf as fitz
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_access_token, hash_password
from app.infrastructure.db.models.admin import Admin, AdminRole


def _make_test_pdf(title: str, text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"{title}\n\n{text}", fontsize=11)
    b = doc.tobytes()
    doc.close()
    return b


@pytest.fixture
async def auth_headers(db_session: AsyncSession) -> dict[str, dict[str, str]]:
    """Create test admins for all roles and return Authorization headers."""
    headers_by_role = {}
    for role in [AdminRole.SUPER_ADMIN, AdminRole.SITE_CURATOR, AdminRole.OPERATOR, AdminRole.VIEWER]:
        admin = Admin(
            username=f"admin_{role.value.lower()}",
            email=f"{role.value.lower()}@karnataka.gov.in",
            hashed_password=hash_password("Secret123!"),
            role=role,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(admin)
        await db_session.flush()

        token = create_access_token(admin_id=admin.id, role=role.value)
        headers_by_role[role.value] = {"Authorization": f"Bearer {token}"}

    await db_session.commit()
    return headers_by_role


@pytest.mark.asyncio
async def test_retrieval_diagnostic_endpoint_unauthorized(client_with_db: httpx.AsyncClient):
    """Verify unauthenticated calls to retrieval diagnostic endpoints are rejected."""
    res = await client_with_db.post("/api/v1/admin/knowledge/retrieval-test", json={"query": "Who built Belur?"})
    assert res.status_code == 401

    res_alias = await client_with_db.post("/api/v1/admin/diagnostics/retrieve", json={"query": "Who built Belur?"})
    assert res_alias.status_code == 401


@pytest.mark.asyncio
async def test_retrieval_diagnostic_empty_active_generation(
    client_with_db: httpx.AsyncClient,
    auth_headers: dict[str, dict[str, str]],
):
    """Verify retrieval diagnostic responds gracefully when no active generation exists."""
    headers = auth_headers["SUPER_ADMIN"]
    res = await client_with_db.post(
        "/api/v1/admin/knowledge/retrieval-test",
        json={"query": "Who built the Belur temple?", "top_k": 5},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["query"] == "Who built the Belur temple?"
    assert data["active_generation_id"] is None
    assert data["final_count"] == 0
    assert len(data["results"]) == 0
    assert "No ACTIVE knowledge generation found" in data["diagnostic_notes"][0]
    assert data["timings_ms"]["total_ms"] >= 0.0


@pytest.mark.asyncio
async def test_retrieval_diagnostic_end_to_end(
    client_with_db: httpx.AsyncClient,
    auth_headers: dict[str, dict[str, str]],
):
    """Verify full end-to-end hybrid retrieval with real document, build, promote, and test query."""
    headers = auth_headers["SUPER_ADMIN"]

    # 1. Upload PDF
    pdf_bytes = _make_test_pdf(
        "Belur Chennakeshava Temple Guide",
        "The Chennakeshava Temple at Belur was commissioned by King Vishnuvardhana of the Hoysala dynasty in 1117 CE. It features a star-shaped soapstone plinth.",
    )
    up_res = await client_with_db.post(
        "/api/v1/admin/documents",
        files={"file": ("belur_guide.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    assert up_res.status_code == 201
    doc_id = up_res.json()["id"]

    # 2. Build Generation & Promote to ACTIVE
    build_res = await client_with_db.post(
        "/api/v1/admin/knowledge/generations/build",
        json={"document_ids": [doc_id], "description": "Test Gen for Retrieval"},
        headers=headers,
    )
    assert build_res.status_code == 201
    gen_id = build_res.json()["id"]

    promote_res = await client_with_db.post(
        f"/api/v1/admin/knowledge/generations/{gen_id}/promote",
        headers=headers,
    )
    assert promote_res.status_code == 200

    # 3. Test Retrieval Diagnostic API
    test_res = await client_with_db.post(
        "/api/v1/admin/knowledge/retrieval-test",
        json={
            "query": "King Vishnuvardhana 1117 CE Belur",
            "top_k": 5,
            "dense_top_k": 10,
            "bm25_top_k": 10,
            "rerank_candidates": 5,
            "enable_reranker": True,
            "filter_noise": True,
            "suppress_duplicates": True,
        },
        headers=headers,
    )
    assert test_res.status_code == 200
    diag = test_res.json()

    assert diag["active_generation_id"] == gen_id
    assert diag["dense_candidates_count"] >= 1
    assert diag["bm25_candidates_count"] >= 1
    assert diag["fused_candidates_count"] >= 1
    assert diag["final_count"] >= 1
    assert len(diag["results"]) >= 1

    top_chunk = diag["results"][0]
    assert top_chunk["final_rank"] == 1
    assert "Vishnuvardhana" in top_chunk["text"]
    assert top_chunk["source_filename"] == "belur_guide.pdf"
    assert top_chunk["page_number"] == 1
    assert top_chunk["dense_rank"] is not None
    assert top_chunk["bm25_rank"] is not None
    assert top_chunk["rrf_score"] is not None
    assert top_chunk["reranker_score"] is not None

    # Timing metrics
    assert "dense_ms" in diag["timings_ms"]
    assert "bm25_ms" in diag["timings_ms"]
    assert "fusion_ms" in diag["timings_ms"]
    assert "rerank_ms" in diag["timings_ms"]
    assert "total_ms" in diag["timings_ms"]
