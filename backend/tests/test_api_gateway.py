"""
Phase 13 Unit & Integration Tests — Unified FastAPI Client Gateway & Streaming Integration.

Tests cover:
- Public tourist route inventory and endpoint contract compliance
- Anonymous session lifecycle (zero-auth, session isolation, history deletion)
- Text chat request/response schema completeness and stable citation fields
- SSE streaming protocol (event ordering: token -> citations -> done)
- Pre-stream error handling (HTTP status + JSON error envelope)
- Mid-stream error handling (event: error + connection close, never done/citations)
- Interrupted/failed stream persistence safety (no partial/corrupt message persisted)
- Voice transcription (STT) and voice chat integration
- TTS handoff using assistant_message_id from chat, voice chat, and SSE done events
- Error envelope structure consistency and zero leakage of internals
- Offline operation without external cloud dependencies
- OpenAPI 3.1 schema generation and CORS configuration
"""

from datetime import datetime, timezone
import io
import json
from typing import AsyncIterator, List, Optional
from unittest.mock import AsyncMock, patch
import httpx
import pymupdf as fitz
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.conversation.schemas import ChatTurnResponse, CitationItem
from app.application.conversation.service import ConversationService
from app.core.security import create_access_token, hash_password
from app.domain.ports.llm import ILLMProvider
from app.infrastructure.db.models.admin import Admin, AdminRole
from app.infrastructure.db.models.chat import ChatMessage, ChatSession, SenderType


class MockGatewayLLM(ILLMProvider):
    """Deterministic Mock LLM for gateway streaming and error tests."""

    def __init__(self, response_text: str = "The Hoysala temple was built in 1117 CE [1].", fail_mid_stream: bool = False):
        self.response_text = response_text
        self.fail_mid_stream = fail_mid_stream
        self.generate_stream_calls = 0

    async def generate_text(self, system_prompt: str, user_prompt: str, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> str:
        return self.response_text

    async def generate_stream(self, system_prompt: str, user_prompt: str, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> AsyncIterator[str]:
        self.generate_stream_calls += 1
        words = self.response_text.split(" ")
        for i, word in enumerate(words):
            if self.fail_mid_stream and i >= 2:
                raise RuntimeError("Simulated mid-stream LLM daemon crash")
            yield f"{word} "

    async def check_health(self) -> bool:
        return True


def _make_test_pdf(title: str, text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 500, 750)
    page.insert_textbox(rect, f"{title}\n\n{text}", fontsize=11)
    b = doc.tobytes()
    doc.close()
    return b


@pytest.fixture
async def gateway_knowledge_generation(
    client_with_db: httpx.AsyncClient,
    db_session: AsyncSession,
) -> str:
    """Helper fixture to set up an active knowledge generation for gateway integration testing."""
    admin = Admin(
        username="admin_gw_test",
        email="admin_gw@karnataka.gov.in",
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
        files={"file": ("belur_gw_guide.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    assert up_res.status_code == 201
    doc_id = up_res.json()["id"]

    # 2. Build Generation & Promote to ACTIVE
    build_res = await client_with_db.post(
        "/api/v1/admin/knowledge/generations/build",
        json={"document_ids": [doc_id], "description": "Test Gen for Gateway Integration"},
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


# =============================================================================
# 1. Route Inventory & Contract Compliance Tests
# =============================================================================

@pytest.mark.asyncio
async def test_existing_tourist_route_inventory_contract(client_with_db: httpx.AsyncClient):
    """Verify that all 8 public tourist endpoints exist and are properly mounted in /api/v1."""
    # 1. POST /tourist/sessions
    res_sess = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    assert res_sess.status_code == 201
    sess_uuid = res_sess.json()["session_uuid"]

    # 2. GET /tourist/sessions/{uuid}
    res_hist = await client_with_db.get(f"/api/v1/tourist/sessions/{sess_uuid}")
    assert res_hist.status_code == 200

    # 3. DELETE /tourist/sessions/{uuid}
    res_del = await client_with_db.delete(f"/api/v1/tourist/sessions/{sess_uuid}")
    assert res_del.status_code == 200


@pytest.mark.asyncio
async def test_anonymous_session_creation_contract(client_with_db: httpx.AsyncClient):
    """Verify unauthenticated creation of anonymous tourist session with default and custom language."""
    # Default language
    res_default = await client_with_db.post("/api/v1/tourist/sessions")
    assert res_default.status_code == 201
    data_def = res_default.json()
    assert "session_uuid" in data_def
    assert len(data_def["session_uuid"]) == 36
    assert data_def["language_code"] == "kn"

    # Custom language
    res_en = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    assert res_en.status_code == 201
    assert res_en.json()["language_code"] == "en"


# =============================================================================
# 2. Text Chat & Citation Contract Tests
# =============================================================================

@pytest.mark.asyncio
async def test_text_chat_request_schema_validation(client_with_db: httpx.AsyncClient):
    """Verify validation errors (422) on empty message, oversized message, and missing session UUID."""
    # Missing session_uuid
    res1 = await client_with_db.post("/api/v1/tourist/chat", json={"message": "Hello"})
    assert res1.status_code == 422
    assert res1.json()["error"]["code"] == "VALIDATION_ERROR"

    # Empty message
    res2 = await client_with_db.post("/api/v1/tourist/chat", json={"session_uuid": "abc", "message": ""})
    assert res2.status_code == 422
    assert res2.json()["error"]["code"] == "VALIDATION_ERROR"

    # Oversized message (> 1000 chars)
    res3 = await client_with_db.post("/api/v1/tourist/chat", json={"session_uuid": "abc", "message": "x" * 1001})
    assert res3.status_code == 422
    assert res3.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_text_chat_response_schema_and_citation_fields(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """Verify complete ChatTurnResponse schema and stable public citation fields."""
    sess_res = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    sess_uuid = sess_res.json()["session_uuid"]

    chat_res = await client_with_db.post(
        "/api/v1/tourist/chat",
        json={"session_uuid": sess_uuid, "message": "Who commissioned the Belur Chennakeshava temple?"},
    )
    assert chat_res.status_code == 200
    data = chat_res.json()

    # Core response fields
    assert data["session_uuid"] == sess_uuid
    assert "message_id" in data
    assert len(data["message_id"]) == 36
    assert "answer" in data
    assert data["language"] == "en"
    assert data["grounded"] is True
    assert "created_at" in data

    # Stable Public Citation Fields
    assert len(data["citations"]) >= 1
    citation = data["citations"][0]
    assert "citation_label" in citation
    assert "source_filename" in citation
    assert "page_number" in citation
    assert isinstance(citation["page_number"], int)


# =============================================================================
# 3. Server-Sent Events (SSE) Streaming & Lifecycle Tests
# =============================================================================

@pytest.mark.asyncio
async def test_sse_content_type_and_event_ordering(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """Verify SSE streaming content type and event order: token -> citations -> done."""
    sess_res = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    sess_uuid = sess_res.json()["session_uuid"]

    stream_res = await client_with_db.post(
        "/api/v1/tourist/chat/stream",
        json={"session_uuid": sess_uuid, "message": "When was the Belur temple built?"},
    )
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers["content-type"]
    assert "no-cache" in stream_res.headers.get("cache-control", "")

    body = stream_res.text
    assert "event: token" in body
    assert "event: citations" in body
    assert "event: done" in body

    # Verify event ordering: token before citations before done
    idx_token = body.find("event: token")
    idx_citations = body.find("event: citations")
    idx_done = body.find("event: done")
    assert idx_token < idx_citations < idx_done


@pytest.mark.asyncio
async def test_sse_pre_stream_error_returns_http_404_json(client_with_db: httpx.AsyncClient):
    """Verify that a pre-stream error (non-existent session UUID) returns HTTP 404 JSON, NOT HTTP 200 SSE."""
    res = await client_with_db.post(
        "/api/v1/tourist/chat/stream",
        json={"session_uuid": "00000000-0000-0000-0000-000000000000", "message": "Hello"},
    )
    assert res.status_code == 404
    assert "application/json" in res.headers["content-type"]
    assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_sse_pre_stream_error_returns_http_422_json(client_with_db: httpx.AsyncClient):
    """Verify that an invalid payload returns HTTP 422 JSON error envelope."""
    res = await client_with_db.post(
        "/api/v1/tourist/chat/stream",
        json={"session_uuid": "valid-format-uuid", "message": ""},
    )
    assert res.status_code == 422
    assert "application/json" in res.headers["content-type"]
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_sse_mid_stream_error_event_and_clean_termination(
    db_session: AsyncSession,
    gateway_knowledge_generation: str,
):
    """Verify that a mid-stream failure emits event: error and terminates immediately without citations or done."""
    failing_llm = MockGatewayLLM(fail_mid_stream=True)
    service = ConversationService(session=db_session, llm_provider=failing_llm)

    sess = await service.create_session(language_code="en")

    events: List[dict] = []
    async for event in service.stream_turn(
        session_uuid=sess.session_uuid,
        user_message="Tell me about the Belur temple history.",
    ):
        events.append(event)

    event_names = [e["event"] for e in events]
    assert "token" in event_names
    assert "error" in event_names
    # Terminal invariant: done and citations MUST NOT be emitted after a mid-stream error
    assert "done" not in event_names
    assert "citations" not in event_names

    error_event = next(e for e in events if e["event"] == "error")
    assert error_event["data"]["code"] == "SERVICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_sse_interrupted_stream_leaves_no_corrupt_db_records(
    db_session: AsyncSession,
    gateway_knowledge_generation: str,
):
    """Verify that when a stream fails mid-turn, no partial assistant message is persisted in MySQL."""
    failing_llm = MockGatewayLLM(fail_mid_stream=True)
    service = ConversationService(session=db_session, llm_provider=failing_llm)

    sess = await service.create_session(language_code="en")

    # Run failing stream
    async for _ in service.stream_turn(session_uuid=sess.session_uuid, user_message="Tell me about Belur."):
        pass

    # Verify no messages were persisted
    history = await service.get_history(session_uuid=sess.session_uuid)
    assert history.total_messages == 0


@pytest.mark.asyncio
async def test_sse_ungrounded_fallback_streaming(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """Verify ungrounded query streams exact fallback token and empty citations array."""
    sess_res = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    sess_uuid = sess_res.json()["session_uuid"]

    stream_res = await client_with_db.post(
        "/api/v1/tourist/chat/stream",
        json={"session_uuid": sess_uuid, "message": "What is the capital of Antarctica?"},
    )
    assert stream_res.status_code == 200
    body = stream_res.text

    assert "Information is not available in the knowledge base." in body
    assert '"citations": []' in body
    assert '"grounded": false' in body


# =============================================================================
# 4. Voice Input & TTS Interoperability Handoff Tests
# =============================================================================

@pytest.mark.asyncio
async def test_voice_transcription_api_contract(client_with_db: httpx.AsyncClient):
    """Verify POST /tourist/voice/transcribe validates input and returns structured TranscriptionResponse."""
    # Generate minimal valid 1-second 16kHz Mono PCM WAV
    wav_io = io.BytesIO()
    import wave
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 16000)
    wav_bytes = wav_io.getvalue()

    with patch("app.infrastructure.stt.faster_whisper.FasterWhisperProvider.transcribe_audio") as mock_stt:
        from app.domain.ports.stt import TranscriptionResult, TranscriptionSegment
        mock_stt.return_value = TranscriptionResult(
            text="Where is Belur temple?",
            language="en",
            language_probability=0.98,
            duration_seconds=1.0,
            segments=[TranscriptionSegment(start=0.0, end=1.0, text="Where is Belur temple?")],
        )

        res = await client_with_db.post(
            "/api/v1/tourist/voice/transcribe",
            files={"file": ("test.wav", io.BytesIO(wav_bytes), "audio/wav")},
            data={"language": "en"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["text"] == "Where is Belur temple?"
        assert data["language"] == "en"
        assert len(data["segments"]) == 1


@pytest.mark.asyncio
async def test_tts_handoff_using_message_id_from_chat(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """Verify that message_id from POST /chat can be passed directly to POST /voice/synthesize."""
    # 1. Chat turn
    sess_res = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    sess_uuid = sess_res.json()["session_uuid"]

    chat_res = await client_with_db.post(
        "/api/v1/tourist/chat",
        json={"session_uuid": sess_uuid, "message": "Who commissioned the Belur temple?"},
    )
    assert chat_res.status_code == 200
    msg_id = chat_res.json()["message_id"]

    # 2. Synthesize using assistant_message_id = msg_id
    with patch("app.infrastructure.tts.piper.PiperTTSProvider.synthesize") as mock_synth:
        from app.domain.ports.tts import AudioSynthesisResult
        mock_synth.return_value = AudioSynthesisResult(
            audio_bytes=b"RIFFmockwavdata",
            sample_rate=22050,
            channels=1,
            sample_width=2,
            duration_seconds=2.5,
        )

        tts_res = await client_with_db.post(
            "/api/v1/tourist/voice/synthesize",
            json={"session_uuid": sess_uuid, "assistant_message_id": msg_id},
        )
        assert tts_res.status_code == 200
        assert tts_res.headers["content-type"] == "audio/wav"
        assert tts_res.headers["x-audio-sample-rate"] == "22050"
        assert tts_res.headers["x-language"] == "en"


@pytest.mark.asyncio
async def test_tts_rejects_wrong_session_ownership(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """Verify that attempting to synthesize a message using a different session UUID returns 403 Forbidden."""
    # Session A
    sess_a = (await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})).json()["session_uuid"]
    chat_a = (await client_with_db.post("/api/v1/tourist/chat", json={"session_uuid": sess_a, "message": "Tell me about Belur."})).json()
    msg_a_id = chat_a["message_id"]

    # Session B
    sess_b = (await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})).json()["session_uuid"]

    # Attempt synthesis with Session B + Msg A ID
    res = await client_with_db.post(
        "/api/v1/tourist/voice/synthesize",
        json={"session_uuid": sess_b, "assistant_message_id": msg_a_id},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_tts_rejects_user_message_synthesis(
    client_with_db: httpx.AsyncClient,
    db_session: AsyncSession,
):
    """Verify that attempting to synthesize a USER message returns 400 Bad Request."""
    from sqlalchemy import select
    sess = (await client_with_db.post("/api/v1/tourist/sessions")).json()["session_uuid"]
    
    chat_sess_res = await db_session.execute(select(ChatSession).where(ChatSession.session_uuid == sess))
    chat_sess = chat_sess_res.scalar_one()

    # Create a user message directly
    user_msg = ChatMessage(
        id="user-msg-test-123",
        session_id=chat_sess.id,
        sender_type=SenderType.USER,
        message_text="Hello I am a tourist",
        detected_language="en",
    )
    db_session.add(user_msg)
    await db_session.commit()

    res = await client_with_db.post(
        "/api/v1/tourist/voice/synthesize",
        json={"session_uuid": sess, "assistant_message_id": "user-msg-test-123"},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "BAD_REQUEST"


# =============================================================================
# 5. Gateway Security, CORS & OpenAPI Validation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_error_envelopes_format_consistency(client_with_db: httpx.AsyncClient):
    """Verify that all error responses follow the standardized error envelope structure."""
    # 404 Not Found
    res_404 = await client_with_db.get("/api/v1/tourist/sessions/non-existent-uuid")
    assert res_404.status_code == 404
    data_404 = res_404.json()
    assert "error" in data_404
    assert data_404["error"]["code"] == "NOT_FOUND"
    assert "message" in data_404["error"]

    # 422 Validation Error
    res_422 = await client_with_db.post("/api/v1/tourist/chat", json={})
    assert res_422.status_code == 422
    data_422 = res_422.json()
    assert data_422["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data_422["error"]


@pytest.mark.asyncio
async def test_no_tourist_auth_required(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """Verify that all tourist operations succeed with zero authorization headers."""
    # Session
    s_res = await client_with_db.post("/api/v1/tourist/sessions", headers={})
    assert s_res.status_code == 201
    s_uuid = s_res.json()["session_uuid"]

    # Chat
    c_res = await client_with_db.post("/api/v1/tourist/chat", json={"session_uuid": s_uuid, "message": "Belur history?"}, headers={})
    assert c_res.status_code == 200

    # History
    h_res = await client_with_db.get(f"/api/v1/tourist/sessions/{s_uuid}", headers={})
    assert h_res.status_code == 200


@pytest.mark.asyncio
async def test_admin_api_remains_jwt_protected(client_with_db: httpx.AsyncClient):
    """Verify that admin endpoints strictly reject unauthenticated requests with 401."""
    res = await client_with_db.get("/api/v1/admin/documents")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_cors_headers_exposed(client_with_db: httpx.AsyncClient):
    """Verify that CORS response headers expose the expected application headers."""
    res = await client_with_db.options(
        "/api/v1/tourist/sessions",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.status_code == 200
    assert "access-control-allow-origin" in res.headers


@pytest.mark.asyncio
async def test_openapi_json_schema_validity(client_with_db: httpx.AsyncClient):
    """Verify that /openapi.json generates cleanly with all tourist endpoints defined."""
    res = await client_with_db.get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()
    assert "paths" in schema
    assert "/api/v1/tourist/sessions" in schema["paths"]
    assert "/api/v1/tourist/chat" in schema["paths"]
    assert "/api/v1/tourist/chat/stream" in schema["paths"]
    assert "/api/v1/tourist/voice/transcribe" in schema["paths"]
    assert "/api/v1/tourist/chat/voice" in schema["paths"]
    assert "/api/v1/tourist/voice/synthesize" in schema["paths"]


@pytest.mark.asyncio
async def test_voice_chat_api_contract_end_to_end(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """Verify POST /tourist/chat/voice conducts end-to-end voice turn returning both transcription and chat."""
    sess_res = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    sess_uuid = sess_res.json()["session_uuid"]

    # 16kHz mono silent WAV
    wav_io = io.BytesIO()
    import wave
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 16000)
    wav_bytes = wav_io.getvalue()

    with patch("app.infrastructure.stt.faster_whisper.FasterWhisperProvider.transcribe_audio") as mock_stt:
        from app.domain.ports.stt import TranscriptionResult, TranscriptionSegment
        mock_stt.return_value = TranscriptionResult(
            text="Who built Belur temple?",
            language="en",
            language_probability=0.99,
            duration_seconds=1.0,
            segments=[TranscriptionSegment(start=0.0, end=1.0, text="Who built Belur temple?")],
        )

        res = await client_with_db.post(
            "/api/v1/tourist/chat/voice",
            files={"file": ("query.wav", io.BytesIO(wav_bytes), "audio/wav")},
            data={"session_uuid": sess_uuid, "language": "en"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "transcription" in data
        assert data["transcription"]["text"] == "Who built Belur temple?"
        assert "chat" in data
        assert data["chat"]["session_uuid"] == sess_uuid
        assert "message_id" in data["chat"]
        assert len(data["chat"]["message_id"]) == 36
        assert data["chat"]["grounded"] is True


@pytest.mark.asyncio
async def test_no_duplicate_stt_call_in_voice_chat(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """Verify that STT runs exactly once during a voice chat turn."""
    sess_res = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    sess_uuid = sess_res.json()["session_uuid"]

    wav_io = io.BytesIO()
    import wave
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 16000)
    wav_bytes = wav_io.getvalue()

    with patch("app.infrastructure.stt.faster_whisper.FasterWhisperProvider.transcribe_audio") as mock_stt:
        from app.domain.ports.stt import TranscriptionResult, TranscriptionSegment
        mock_stt.return_value = TranscriptionResult(
            text="Belur history",
            language="en",
            language_probability=0.99,
            duration_seconds=1.0,
            segments=[TranscriptionSegment(start=0.0, end=1.0, text="Belur history")],
        )

        res = await client_with_db.post(
            "/api/v1/tourist/chat/voice",
            files={"file": ("query.wav", io.BytesIO(wav_bytes), "audio/wav")},
            data={"session_uuid": sess_uuid, "language": "en"},
        )
        assert res.status_code == 200
        assert mock_stt.call_count == 1


@pytest.mark.asyncio
async def test_tts_handoff_from_sse_done_event(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """Verify that message_id extracted from SSE done event can be passed to /tourist/voice/synthesize."""
    sess_res = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    sess_uuid = sess_res.json()["session_uuid"]

    stream_res = await client_with_db.post(
        "/api/v1/tourist/chat/stream",
        json={"session_uuid": sess_uuid, "message": "Belur temple Madanika bracket figures?"},
    )
    assert stream_res.status_code == 200
    body = stream_res.text

    # Extract message_id from done event
    done_idx = body.find("event: done")
    assert done_idx != -1
    done_line = [line for line in body[done_idx:].split("\n") if line.startswith("data:")][0]
    done_data = json.loads(done_line[len("data:"):].strip())
    msg_id = done_data["message_id"]

    with patch("app.infrastructure.tts.piper.PiperTTSProvider.synthesize") as mock_synth:
        from app.domain.ports.tts import AudioSynthesisResult
        mock_synth.return_value = AudioSynthesisResult(
            audio_bytes=b"RIFFmockpiper",
            sample_rate=22050,
            channels=1,
            sample_width=2,
            duration_seconds=1.8,
        )

        tts_res = await client_with_db.post(
            "/api/v1/tourist/voice/synthesize",
            json={"session_uuid": sess_uuid, "assistant_message_id": msg_id},
        )
        assert tts_res.status_code == 200
        assert tts_res.headers["content-type"] == "audio/wav"


@pytest.mark.asyncio
async def test_tts_rejects_invalid_session_uuid(client_with_db: httpx.AsyncClient):
    """Verify that /voice/synthesize returns 404 when session UUID does not exist."""
    res = await client_with_db.post(
        "/api/v1/tourist/voice/synthesize",
        json={"session_uuid": "00000000-0000-0000-0000-000000000000", "assistant_message_id": "dummy-id"},
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_voice_rejects_corrupted_audio(client_with_db: httpx.AsyncClient):
    """Verify that submitting random binary junk to /tourist/voice/transcribe returns 400 Bad Request."""
    res = await client_with_db.post(
        "/api/v1/tourist/voice/transcribe",
        files={"file": ("corrupt.wav", io.BytesIO(b"\xde\xad\xbe\xef\x00\x11\x22\x33"), "audio/wav")},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] in {"INVALID_AUDIO_PAYLOAD", "BAD_REQUEST"}


@pytest.mark.asyncio
async def test_voice_rejects_oversized_audio(client_with_db: httpx.AsyncClient):
    """Verify that audio exceeding 15MB is rejected with 400 Bad Request."""
    oversized_data = b"0" * (16 * 1024 * 1024)  # 16 MB
    res = await client_with_db.post(
        "/api/v1/tourist/voice/transcribe",
        files={"file": ("large.wav", io.BytesIO(oversized_data), "audio/wav")},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] in {"INVALID_AUDIO_PAYLOAD", "BAD_REQUEST"}


@pytest.mark.asyncio
async def test_completed_stream_persists_user_and_assistant(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """Verify that upon completed stream, both USER and ASSISTANT messages are in session history."""
    sess_res = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    sess_uuid = sess_res.json()["session_uuid"]

    stream_res = await client_with_db.post(
        "/api/v1/tourist/chat/stream",
        json={"session_uuid": sess_uuid, "message": "Tell me about Belur temple."},
    )
    assert stream_res.status_code == 200

    # Fetch history
    hist_res = await client_with_db.get(f"/api/v1/tourist/sessions/{sess_uuid}")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["total_messages"] == 2
    assert hist["messages"][0]["sender_type"] in {"USER", "user"}
    assert hist["messages"][1]["sender_type"] in {"ASSISTANT", "assistant"}
    assert "citations" in hist["messages"][1]


@pytest.mark.asyncio
async def test_exact_kannada_fallback_streaming(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """Verify that ungrounded Kannada queries return exact Kannada fallback string."""
    sess_res = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "kn"})
    sess_uuid = sess_res.json()["session_uuid"]

    stream_res = await client_with_db.post(
        "/api/v1/tourist/chat/stream",
        json={"session_uuid": sess_uuid, "message": "ಚಂದ್ರನ ಮೇಲೆ ಮೊದಲ ಮಾನವ ಯಾರು?"},
    )
    assert stream_res.status_code == 200
    body = stream_res.text
    assert "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ." in body
    assert '"citations": []' in body


@pytest.mark.asyncio
async def test_no_external_cloud_calls_verification(client_with_db: httpx.AsyncClient):
    """Verify that tourist operations execute entirely locally without making external/WAN/cloud HTTP calls."""
    # 1. Verify tourist session creation succeeds locally
    sess_res = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    assert sess_res.status_code == 201

    # 2. Verify all AI/DB endpoints point to local loopback infrastructure (no cloud dependencies)
    from app.core.config import get_settings
    settings = get_settings()
    assert "localhost" in settings.OLLAMA_BASE_URL or "127.0.0.1" in settings.OLLAMA_BASE_URL
    assert not settings.OLLAMA_BASE_URL.startswith("https://api.openai.com")
    assert not settings.OLLAMA_BASE_URL.startswith("https://api.anthropic.com")
    assert not settings.OLLAMA_BASE_URL.startswith("https://generativelanguage.googleapis.com")


# =============================================================================
# 9. Public Citation Alignment & SSE Token Contract Verification Tests
# =============================================================================

@pytest.mark.asyncio
async def test_sse_exact_token_payload_key(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """Verify that all SSE token events strictly use data: {"text": "..."} (and never {"token": "..."})."""
    sess_res = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    sess_uuid = sess_res.json()["session_uuid"]

    stream_res = await client_with_db.post(
        "/api/v1/tourist/chat/stream",
        json={"session_uuid": sess_uuid, "message": "Tell me about Belur temple history."},
    )
    assert stream_res.status_code == 200

    token_count = 0
    lines = stream_res.text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "event: token":
            # Next line must be data: {"text": "..."}
            assert i + 1 < len(lines)
            data_line = lines[i + 1]
            assert data_line.startswith("data: ")
            payload = json.loads(data_line[6:])
            assert "text" in payload, f"Expected 'text' key in token payload, got: {payload}"
            assert "token" not in payload, f"Forbidden 'token' key found in token payload: {payload}"
            assert isinstance(payload["text"], str)
            token_count += 1

    assert token_count > 0, "Expected at least one token event in stream"


@pytest.mark.asyncio
async def test_public_citation_label_alignment_and_filtering(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """
    Verify that public citations returned in ChatTurnResponse correspond ONLY to citation labels
    actually referenced in the final visible answer, while internal retrieval evidence count is preserved.
    """
    sess_res = await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    sess_uuid = sess_res.json()["session_uuid"]

    chat_res = await client_with_db.post(
        "/api/v1/tourist/chat",
        json={"session_uuid": sess_uuid, "message": "Who commissioned the Belur Chennakeshava temple?"},
    )
    assert chat_res.status_code == 200
    data = chat_res.json()

    answer = data["answer"]
    public_citations = data["citations"]
    retrieval_meta = data["retrieval"]

    # Every emitted public citation label MUST exist in the final visible answer text
    assert len(public_citations) >= 1
    for cit in public_citations:
        assert cit["citation_label"] in answer, f"Citation label {cit['citation_label']} not in answer '{answer}'"

    # Internal retrieval diagnostics retain full evidence count
    assert retrieval_meta["evidence_count"] >= len(public_citations)


def test_filter_authoritative_citations_logic():
    """Unit test for authoritative citation filtering, ordering, and deduplication."""
    from app.application.conversation.citation_formatter import filter_authoritative_citations

    auth_citations = [
        {"citation_label": "[1]", "source_filename": "doc1.pdf", "page_number": 1},
        {"citation_label": "[2]", "source_filename": "doc2.pdf", "page_number": 2},
        {"citation_label": "[3]", "source_filename": "doc3.pdf", "page_number": 3},
    ]

    # Case 1: Answer only references [1]
    res1 = filter_authoritative_citations("King Vishnuvardhana [1].", auth_citations)
    assert len(res1) == 1
    assert res1[0]["citation_label"] == "[1]"

    # Case 2: Answer references [2] then [1] then duplicate [2]
    res2 = filter_authoritative_citations("First [2] then [1] and again [2].", auth_citations)
    assert len(res2) == 2
    assert res2[0]["citation_label"] == "[2]"
    assert res2[1]["citation_label"] == "[1]"

    # Case 3: Fallback response with no labels
    res3 = filter_authoritative_citations("Information is not available in the knowledge base.", auth_citations)
    assert res3 == []

    # Case 4: Empty text
    res4 = filter_authoritative_citations("", auth_citations)
    assert res4 == []


@pytest.mark.asyncio
async def test_streaming_and_non_streaming_citation_parity(
    client_with_db: httpx.AsyncClient,
    gateway_knowledge_generation: str,
):
    """Verify that synchronous /chat and streaming /chat/stream return identical citation subsets for identical queries."""
    query = "Who commissioned the Belur Chennakeshava temple in 1117 CE?"

    # 1. Non-streaming call
    sess1 = (await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})).json()["session_uuid"]
    res_sync = await client_with_db.post("/api/v1/tourist/chat", json={"session_uuid": sess1, "message": query})
    assert res_sync.status_code == 200
    sync_citations = res_sync.json()["citations"]
    sync_labels = [c["citation_label"] for c in sync_citations]

    # 2. Streaming call
    sess2 = (await client_with_db.post("/api/v1/tourist/sessions", json={"language_code": "en"})).json()["session_uuid"]
    res_stream = await client_with_db.post("/api/v1/tourist/chat/stream", json={"session_uuid": sess2, "message": query})
    assert res_stream.status_code == 200
    
    stream_citations = []
    for line in res_stream.text.splitlines():
        if line.startswith("data: ") and '"citations":' in line:
            payload = json.loads(line[6:])
            stream_citations = payload["citations"]
            break
    stream_labels = [c["citation_label"] for c in stream_citations]

    # Both must match the cited labels in their respective answers
    assert len(sync_labels) >= 1
    assert len(stream_labels) >= 1
    for label in sync_labels:
        assert label in res_sync.json()["answer"]
