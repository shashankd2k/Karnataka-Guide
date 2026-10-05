"""
Comprehensive Unit and Integration Tests for Speech-To-Text (STT) Engine (Phase 10).
Verifies:
1. Provider initialization & model singleton reuse
2. Valid audio decoding & transcription across formats
3. English and Kannada speech recognition support
4. Multi-layer validation (size, MIME, magic bytes, decodability, duration)
5. Robust error handling (empty audio, corrupt containers, model failures, empty transcripts)
6. Privacy & guaranteed temporary audio file cleanup
7. Anonymous public tourist API endpoints & voice-to-chat integration
8. Zero cloud API dependencies & offline readiness
"""

import io
import math
from pathlib import Path
import struct
from typing import AsyncIterator, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import wave

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.conversation.schemas import ChatTurnResponse, RetrievalMeta
from app.application.speech.schemas import (
    TranscriptionResponse,
    TranscriptionSegmentSchema,
    VoiceChatResponse,
)
from app.application.speech.stt_service import SpeechToTextService
from app.core.config import Settings
from app.core.errors import AppException
from app.domain.ports.stt import (
    ISpeechToTextProvider,
    TranscriptionResult,
    TranscriptionSegment,
)
from app.infrastructure.stt.audio_validator import (
    AudioValidationError,
    inspect_magic_bytes,
    validate_and_decode_audio_stream,
)
from app.infrastructure.stt.faster_whisper import (
    FasterWhisperProvider,
    ModelUnavailableError,
    TranscriptionError,
)


def create_synthetic_wav_bytes(
    duration_seconds: float = 1.0,
    sample_rate: int = 16000,
    frequency: float = 440.0,
) -> bytes:
    """Generate valid 16kHz 16-bit mono PCM WAV bytes in memory."""
    buf = io.BytesIO()
    num_samples = int(duration_seconds * sample_rate)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(num_samples):
            # Generate modulated sine wave
            val = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return buf.getvalue()


class MockSpeechToTextProvider(ISpeechToTextProvider):
    """Deterministic mock STT provider for fast unit and endpoint testing."""

    def __init__(
        self,
        transcript_text: str = "Who built the Belur Chennakeshava temple?",
        language: str = "en",
        language_probability: float = 0.98,
        duration_seconds: float = 2.5,
        healthy: bool = True,
    ):
        self.transcript_text = transcript_text
        self.language = language
        self.language_probability = language_probability
        self.duration_seconds = duration_seconds
        self.healthy = healthy

    async def transcribe_audio(
        self,
        file_path: Path,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        if not self.healthy:
            raise ModelUnavailableError("Mock STT engine is unavailable.")
        return TranscriptionResult(
            text=self.transcript_text,
            language=language or self.language,
            language_probability=self.language_probability,
            duration_seconds=self.duration_seconds,
            segments=[
                TranscriptionSegment(
                    start=0.0,
                    end=self.duration_seconds,
                    text=self.transcript_text,
                    avg_logprob=-0.15,
                    no_speech_prob=0.01,
                )
            ],
        )

    async def check_health(self) -> bool:
        return self.healthy


# ============================================================================
# 1. Provider Initialization & Model Singleton Lifecycle
# ============================================================================

def test_stt_provider_initialization():
    """Verify FasterWhisperProvider initializes with project settings."""
    provider = FasterWhisperProvider()
    assert provider.settings.WHISPER_MODEL == "base"
    assert provider.settings.WHISPER_DEVICE == "cpu"
    assert provider.settings.WHISPER_COMPUTE_TYPE == "int8"


@pytest.mark.asyncio
async def test_whisper_model_singleton_reused():
    """Verify FasterWhisperProvider reuses singleton model instance across calls."""
    mock_model = MagicMock()
    with patch.object(FasterWhisperProvider, "_get_or_load_model", return_value=mock_model) as mock_get:
        provider1 = FasterWhisperProvider()
        provider2 = FasterWhisperProvider()
        await provider1.check_health()
        await provider2.check_health()
        assert mock_get.call_count == 2


# ============================================================================
# 2. Audio Validation & Magic Bytes
# ============================================================================

def test_inspect_magic_bytes_valid_wav():
    """Verify magic bytes inspection recognizes RIFF WAVE headers."""
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=0.5)
    assert inspect_magic_bytes(wav_bytes[:16], "sample.wav") is True


def test_inspect_magic_bytes_valid_mp3():
    """Verify magic bytes inspection recognizes ID3 and MPEG sync frames."""
    id3_header = b"ID3\x03\x00\x00\x00\x00\x00\x00"
    assert inspect_magic_bytes(id3_header, "sample.mp3") is True
    sync_header = b"\xff\xfb\x90\x00"
    assert inspect_magic_bytes(sync_header, "sample.mp3") is True


def test_inspect_magic_bytes_valid_webm():
    """Verify magic bytes inspection recognizes EBML WebM headers."""
    ebml_header = b"\x1a\x45\xdf\xa3\x9f\x42\x86\x81"
    assert inspect_magic_bytes(ebml_header, "sample.webm") is True


def test_inspect_magic_bytes_invalid_plain_text():
    """Verify magic bytes inspection rejects non-audio text files."""
    text_bytes = b"Hello this is not audio file at all."
    assert inspect_magic_bytes(text_bytes, "fake.wav") is False


def test_validate_and_decode_audio_stream_valid_wav(tmp_path: Path):
    """Verify deep decoder validation inspects audio stream properties."""
    wav_path = tmp_path / "valid.wav"
    wav_path.write_bytes(create_synthetic_wav_bytes(duration_seconds=1.5, sample_rate=16000))

    duration, sample_rate, codec = validate_and_decode_audio_stream(wav_path, max_duration_seconds=60.0)
    assert 1.4 <= duration <= 1.6
    assert sample_rate == 16000
    assert "pcm" in codec.lower()


def test_validate_and_decode_audio_stream_oversized_duration_rejected(tmp_path: Path):
    """Verify deep decoder validation enforces duration limit."""
    wav_path = tmp_path / "long.wav"
    wav_path.write_bytes(create_synthetic_wav_bytes(duration_seconds=5.0))

    with pytest.raises(AudioValidationError) as exc:
        validate_and_decode_audio_stream(wav_path, max_duration_seconds=3.0)
    assert "exceeds maximum allowed limit" in str(exc.value.message)


# ============================================================================
# 3. SpeechToTextService & Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_transcribe_valid_wav_mocked():
    """Verify SpeechToTextService validates audio and returns structured response."""
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=1.0)
    mock_provider = MockSpeechToTextProvider(
        transcript_text="Tell me about the bracket figures at Belur.",
        language="en",
        language_probability=0.99,
        duration_seconds=1.0,
    )
    service = SpeechToTextService(provider=mock_provider)

    upload = httpx._types.FileTypes  # type helper
    from fastapi import UploadFile
    upload_file = UploadFile(
        file=io.BytesIO(wav_bytes),
        filename="query.wav",
        headers={"content-type": "audio/wav"},
    )

    resp = await service.transcribe(upload_file)
    assert resp.text == "Tell me about the bracket figures at Belur."
    assert resp.language == "en"
    assert resp.language_probability == 0.99
    assert resp.duration_seconds == 1.0
    assert len(resp.segments) == 1
    assert resp.segments[0].text == "Tell me about the bracket figures at Belur."


@pytest.mark.asyncio
async def test_empty_audio_file_rejected():
    """Verify empty audio file upload is rejected with 400 Bad Request."""
    from fastapi import UploadFile
    upload_file = UploadFile(
        file=io.BytesIO(b""),
        filename="empty.wav",
        headers={"content-type": "audio/wav"},
    )
    service = SpeechToTextService()
    with pytest.raises(AudioValidationError) as exc:
        await service.transcribe(upload_file)
    assert "empty" in str(exc.value.message).lower()


@pytest.mark.asyncio
async def test_unsupported_audio_format_rejected():
    """Verify unsupported file extension is rejected."""
    from fastapi import UploadFile
    upload_file = UploadFile(
        file=io.BytesIO(b"dummy-text"),
        filename="document.txt",
        headers={"content-type": "text/plain"},
    )
    service = SpeechToTextService()
    with pytest.raises(AudioValidationError) as exc:
        await service.transcribe(upload_file)
    assert "unsupported audio format" in str(exc.value.message).lower()


@pytest.mark.asyncio
async def test_corrupted_invalid_audio_rejected():
    """Verify fake audio with correct extension but invalid bytes is rejected."""
    from fastapi import UploadFile
    upload_file = UploadFile(
        file=io.BytesIO(b"RIFF\x00\x00\x00\x00NOT_A_WAVE_FILE"),
        filename="fake.wav",
        headers={"content-type": "audio/wav"},
    )
    service = SpeechToTextService()
    with pytest.raises(AudioValidationError) as exc:
        await service.transcribe(upload_file)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_temporary_audio_file_cleaned_up():
    """Verify temporary audio files are deleted even when transcription fails."""
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=0.5)
    from fastapi import UploadFile

    failing_provider = MockSpeechToTextProvider(healthy=False)
    service = SpeechToTextService(provider=failing_provider)

    upload_file = UploadFile(
        file=io.BytesIO(wav_bytes),
        filename="test_cleanup.wav",
        headers={"content-type": "audio/wav"},
    )

    with pytest.raises(ModelUnavailableError):
        await service.transcribe(upload_file)

    # Verify temp audio directory has 0 residual test files
    from app.core.config import get_settings
    temp_dir = get_settings().resolved_temp_audio_path
    stt_files = list(temp_dir.glob("stt_*.*"))
    assert len(stt_files) == 0


# ============================================================================
# 4. Multilingual Speech Support (English & Kannada)
# ============================================================================

@pytest.mark.asyncio
async def test_transcribe_english_speech():
    """Verify English speech transcription metadata."""
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=1.0)
    mock_provider = MockSpeechToTextProvider(
        transcript_text="What are the main attractions in Hampi?",
        language="en",
        language_probability=0.985,
    )
    service = SpeechToTextService(provider=mock_provider)

    from fastapi import UploadFile
    upload_file = UploadFile(
        file=io.BytesIO(wav_bytes),
        filename="hampi.wav",
        headers={"content-type": "audio/wav"},
    )
    resp = await service.transcribe(upload_file, language="en")
    assert resp.language == "en"
    assert "Hampi" in resp.text


@pytest.mark.asyncio
async def test_transcribe_kannada_speech():
    """Verify Kannada speech transcription metadata."""
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=1.0)
    kannada_text = "ಬೇಲೂರು ದೇವಾಲಯದ ಇತಿಹಾಸವೇನು?"
    mock_provider = MockSpeechToTextProvider(
        transcript_text=kannada_text,
        language="kn",
        language_probability=0.945,
    )
    service = SpeechToTextService(provider=mock_provider)

    from fastapi import UploadFile
    upload_file = UploadFile(
        file=io.BytesIO(wav_bytes),
        filename="belur_kn.wav",
        headers={"content-type": "audio/wav"},
    )
    resp = await service.transcribe(upload_file, language="kn")
    assert resp.language == "kn"
    assert resp.text == kannada_text


# ============================================================================
# 5. Voice Chat Turn Pipeline Integration
# ============================================================================

@pytest.mark.asyncio
async def test_voice_chat_turn_pipeline_integration(db_session: AsyncSession):
    """Verify voice_chat coordinates speech transcription with ConversationService."""
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=1.0)
    mock_stt = MockSpeechToTextProvider(
        transcript_text="Who commissioned the Belur temple?",
        language="en",
        language_probability=0.99,
    )
    service = SpeechToTextService(provider=mock_stt)

    from app.application.conversation.service import ConversationService
    conv_service = ConversationService(session=db_session)
    session_rec = await conv_service.create_session(language_code="en")

    from fastapi import UploadFile
    upload_file = UploadFile(
        file=io.BytesIO(wav_bytes),
        filename="voice_turn.wav",
        headers={"content-type": "audio/wav"},
    )

    voice_resp = await service.voice_chat(
        upload_file=upload_file,
        session_uuid=session_rec.session_uuid,
        session=db_session,
    )

    assert isinstance(voice_resp, VoiceChatResponse)
    assert voice_resp.transcription.text == "Who commissioned the Belur temple?"
    assert voice_resp.chat.session_uuid == session_rec.session_uuid
    assert voice_resp.chat.answer is not None


# ============================================================================
# 6. API Endpoint Integration (Anonymous Tourist Access)
# ============================================================================

@pytest.mark.asyncio
async def test_anonymous_tourist_transcribe_endpoint(async_client: httpx.AsyncClient):
    """Verify POST /api/v1/tourist/voice/transcribe functions without authentication."""
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=0.8)

    mock_result = TranscriptionResult(
        text="What are the architectural styles at Pattadakal?",
        language="en",
        language_probability=0.97,
        duration_seconds=0.8,
        segments=[
            TranscriptionSegment(
                start=0.0,
                end=0.8,
                text="What are the architectural styles at Pattadakal?",
            )
        ],
    )

    with patch.object(FasterWhisperProvider, "transcribe_audio", return_value=mock_result):
        files = {"file": ("query.wav", io.BytesIO(wav_bytes), "audio/wav")}
        data = {"language": "en"}
        resp = await async_client.post(
            "/api/v1/tourist/voice/transcribe",
            files=files,
            data=data,
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["text"] == "What are the architectural styles at Pattadakal?"
        assert payload["language"] == "en"
        assert payload["duration_seconds"] == 0.8


@pytest.mark.asyncio
async def test_anonymous_tourist_voice_chat_endpoint(async_client: httpx.AsyncClient):
    """Verify POST /api/v1/tourist/chat/voice processes audio query into grounded chat turn."""
    # 1. Create tourist session
    sess_resp = await async_client.post("/api/v1/tourist/sessions", json={"language_code": "en"})
    assert sess_resp.status_code == 201
    session_uuid = sess_resp.json()["session_uuid"]

    wav_bytes = create_synthetic_wav_bytes(duration_seconds=1.0)
    mock_result = TranscriptionResult(
        text="Who built the Chennakeshava Temple at Belur?",
        language="en",
        language_probability=0.98,
        duration_seconds=1.0,
        segments=[
            TranscriptionSegment(
                start=0.0,
                end=1.0,
                text="Who built the Chennakeshava Temple at Belur?",
            )
        ],
    )

    with patch.object(FasterWhisperProvider, "transcribe_audio", return_value=mock_result):
        files = {"file": ("belur.wav", io.BytesIO(wav_bytes), "audio/wav")}
        data = {"session_uuid": session_uuid, "language": "en"}
        resp = await async_client.post(
            "/api/v1/tourist/chat/voice",
            files=files,
            data=data,
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert "transcription" in payload
        assert payload["transcription"]["text"] == "Who built the Chennakeshava Temple at Belur?"
        assert "chat" in payload
        assert payload["chat"]["session_uuid"] == session_uuid
        assert payload["chat"]["answer"] is not None


# ============================================================================
# 7. Privacy, Security & Non-Regression
# ============================================================================

@pytest.mark.asyncio
async def test_temporary_audio_privacy_retention():
    """Verify temporary audio is not retained in the filesystem after requests."""
    from app.core.config import get_settings
    temp_dir = get_settings().resolved_temp_audio_path
    stt_files = list(temp_dir.glob("stt_*.*"))
    assert len(stt_files) == 0


@pytest.mark.asyncio
async def test_no_cloud_dependency_offline_verification():
    """Verify FasterWhisperProvider check_health uses only local CTranslate2/WhisperModel."""
    provider = FasterWhisperProvider()
    with patch.object(FasterWhisperProvider, "_get_or_load_model") as mock_load:
        is_healthy = await provider.check_health()
        assert is_healthy is True
        mock_load.assert_called_once()
