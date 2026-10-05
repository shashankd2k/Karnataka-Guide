"""
Integration tests for public, unauthenticated tourist conversation APIs.
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
    rect = fitz.Rect(50, 50, 500, 750)
    page.insert_textbox(rect, f"{title}\n\n{text}", fontsize=11)
    b = doc.tobytes()
    doc.close()
    return b


@pytest.fixture
async def active_knowledge_generation(
    client_with_db: httpx.AsyncClient,
    db_session: AsyncSession,
) -> str:
    """Helper fixture to set up an active knowledge generation for tourist chat testing."""
    admin = Admin(
        username="admin_tourist_test",
        email="admin_tourist@karnataka.gov.in",
        hashed_password=hash_password("Secret123!"),
        role=AdminRole.SUPER_ADMIN,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.flush()

    token = create_access_token(admin_id=admin.id, role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Upload PDF
    pdf_bytes = _make_test_pdf(
        "Belur Chennakeshava Temple Guide",
        "The Chennakeshava Temple at Belur was commissioned by King Vishnuvardhana of the Hoysala dynasty in 1117 CE to celebrate the Battle of Talakadu. It features 42 Madanika bracket figures.",
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
        json={"document_ids": [doc_id], "description": "Test Gen for Tourist Chat"},
        headers=headers,
    )
    assert build_res.status_code == 201
    gen_id = build_res.json()["id"]

    promote_res = await client_with_db.post(
        f"/api/v1/admin/knowledge/generations/{gen_id}/promote",
        headers=headers,
    )
    assert promote_res.status_code == 200
    return gen_id


@pytest.mark.asyncio
async def test_create_tourist_session(client_with_db: httpx.AsyncClient):
    """Verify unauthenticated creation of anonymous tourist session."""
    resp = await client_with_db.post(
        "/api/v1/tourist/sessions",
        json={"language_code": "kn"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "session_uuid" in data
    assert len(data["session_uuid"]) == 36
    assert data["language_code"] == "kn"


@pytest.mark.asyncio
async def test_chat_turn_grounded_english(
    client_with_db: httpx.AsyncClient,
    active_knowledge_generation: str,
):
    """Verify single-turn grounded tourist query in English with citations."""
    # 1. Create session
    sess_resp = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    session_uuid = sess_resp.json()["session_uuid"]

    # 2. Ask grounded question
    chat_resp = await client_with_db.post(
        "/api/v1/tourist/chat",
        json={
            "session_uuid": session_uuid,
            "message": "Who commissioned the Belur Chennakeshava temple and why?",
        },
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert data["session_uuid"] == session_uuid
    assert data["grounded"] is True
    assert data["language"] == "en"
    assert len(data["citations"]) > 0
    assert data["citations"][0]["citation_label"] == "[1]"
    assert data["citations"][0]["source_filename"] == "belur_guide.pdf"
    assert data["citations"][0]["page_number"] == 1
    assert "[1]" in data["answer"]


@pytest.mark.asyncio
async def test_chat_turn_multi_turn_follow_up(
    client_with_db: httpx.AsyncClient,
    active_knowledge_generation: str,
):
    """Verify multi-turn follow-up context resolution."""
    # 1. Create session
    sess_resp = await client_with_db.post("/api/v1/tourist/sessions")
    session_uuid = sess_resp.json()["session_uuid"]

    # 2. Turn 1: Primary subject
    turn1 = await client_with_db.post(
        "/api/v1/tourist/chat",
        json={
            "session_uuid": session_uuid,
            "message": "Tell me about the Belur Chennakeshava Temple.",
        },
    )
    assert turn1.status_code == 200
    assert turn1.json()["grounded"] is True

    # 3. Turn 2: Follow-up question with pronoun "it"
    turn2 = await client_with_db.post(
        "/api/v1/tourist/chat",
        json={
            "session_uuid": session_uuid,
            "message": "When was it built?",
        },
    )
    assert turn2.status_code == 200
    data2 = turn2.json()
    assert data2["grounded"] is True
    assert data2["retrieval"]["resolved_query"] is not None
    assert "Belur Chennakeshava Temple" in data2["retrieval"]["resolved_query"]
    assert "1117" in data2["answer"]


@pytest.mark.asyncio
async def test_chat_turn_unsupported_query_english_fallback(
    client_with_db: httpx.AsyncClient,
    active_knowledge_generation: str,
):
    """Verify unsupported query returns English fallback and zero citations."""
    sess_resp = await client_with_db.post("/api/v1/tourist/sessions")
    session_uuid = sess_resp.json()["session_uuid"]

    chat_resp = await client_with_db.post(
        "/api/v1/tourist/chat",
        json={
            "session_uuid": session_uuid,
            "message": "What is the capital of France and how many people live there?",
        },
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert data["grounded"] is False
    assert data["answer"] == "Information is not available in the knowledge base."
    assert len(data["citations"]) == 0


@pytest.mark.asyncio
async def test_chat_turn_unsupported_query_kannada_fallback(
    client_with_db: httpx.AsyncClient,
    active_knowledge_generation: str,
):
    """Verify unsupported query in Kannada returns Kannada fallback."""
    sess_resp = await client_with_db.post("/api/v1/tourist/sessions")
    session_uuid = sess_resp.json()["session_uuid"]

    chat_resp = await client_with_db.post(
        "/api/v1/tourist/chat",
        json={
            "session_uuid": session_uuid,
            "message": "ಪ್ಯಾರಿಸ್ ಫ್ರಾನ್ಸ್ ದೇಶದ ರಾಜಧಾನಿ ಬಗ್ಗೆ ಹೇಳಿ",
        },
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert data["grounded"] is False
    assert data["language"] == "kn"
    assert data["answer"] == "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."
    assert len(data["citations"]) == 0


@pytest.mark.asyncio
async def test_session_history_and_deletion(
    client_with_db: httpx.AsyncClient,
    active_knowledge_generation: str,
):
    """Verify message history retrieval and privacy deletion."""
    # 1. Create session
    sess_resp = await client_with_db.post("/api/v1/tourist/sessions")
    session_uuid = sess_resp.json()["session_uuid"]

    # 2. Send 2 questions
    await client_with_db.post(
        "/api/v1/tourist/chat",
        json={"session_uuid": session_uuid, "message": "Who built Belur temple?"},
    )
    await client_with_db.post(
        "/api/v1/tourist/chat",
        json={"session_uuid": session_uuid, "message": "What year was it?"},
    )

    # 3. Retrieve history (4 messages: 2 USER + 2 ASSISTANT)
    hist_resp = await client_with_db.get(f"/api/v1/tourist/sessions/{session_uuid}")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert hist_data["total_messages"] == 4
    assert hist_data["messages"][0]["sender_type"] == "USER"
    assert hist_data["messages"][1]["sender_type"] == "ASSISTANT"

    # 4. Clear history
    del_resp = await client_with_db.delete(f"/api/v1/tourist/sessions/{session_uuid}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted_messages_count"] == 4

    # 5. Verify history is empty
    hist_after = await client_with_db.get(f"/api/v1/tourist/sessions/{session_uuid}")
    assert hist_after.status_code == 200
    assert hist_after.json()["total_messages"] == 0


@pytest.mark.asyncio
async def test_invalid_session_uuid_returns_404(client_with_db: httpx.AsyncClient):
    """Verify invalid/nonexistent session UUID returns 404 Not Found."""
    resp = await client_with_db.post(
        "/api/v1/tourist/chat",
        json={
            "session_uuid": "00000000-0000-0000-0000-000000000000",
            "message": "Hello",
        },
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_oversized_message_rejected(client_with_db: httpx.AsyncClient):
    """Verify messages > 1000 characters are rejected with 422."""
    resp = await client_with_db.post(
        "/api/v1/tourist/chat",
        json={
            "session_uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "message": "A" * 1001,
        },
    )
    assert resp.status_code == 422
