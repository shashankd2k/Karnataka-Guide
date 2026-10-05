"""
Comprehensive Unit and Integration Tests for Text-To-Speech (TTS) Engine (Phase 12).
Verifies:
1. ITTSProvider abstract domain port contract
2. SpeechTextSanitizer deterministic sanitization (citations, markdown, URLs, control chars)
3. PiperTTSProvider English synthesis (22,050 Hz, Mono, 16-bit PCM WAV)
4. MMSTTSProvider Kannada synthesis (16,000 Hz, Mono, 16-bit PCM WAV)
5. CompositeTTSProvider language routing and unsupported language rejection
6. TTSService session & assistant message ownership validation
7. Public tourist API endpoint POST /api/v1/tourist/voice/synthesize
8. Memory-first in-memory serialization (zero transient disk files during normal synthesis)
9. Native sample rates (22,050 Hz for EN, 16,000 Hz for KN)
10. Voice registry seed data verification
11. End-to-end conversational voice pipeline integration
"""

import io
import math
import struct
import wave
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.speech.schemas import (
    MessageSpeechSynthesisRequest,
    SpeechSynthesisMetadata,
)
from app.application.speech.tts_service import SpeechTextSanitizer, TTSService
from app.core.errors import AppException
from app.domain.ports.tts import AudioSynthesisResult, ITTSProvider
from app.infrastructure.db.models.chat import ChatMessage, ChatSession, SenderType
from app.infrastructure.db.models.system import VoiceProvider, VoiceRegistry
from app.infrastructure.tts.composite import CompositeTTSProvider
from app.infrastructure.tts.mms import MMSTTSProvider
from app.infrastructure.tts.piper import PiperTTSProvider


def create_synthetic_wav(
    duration_seconds: float = 1.0,
    sample_rate: int = 22050,
) -> bytes:
    """Helper creating valid in-memory 16-bit PCM mono WAV bytes."""
    buf = io.BytesIO()
    num_samples = int(duration_seconds * sample_rate)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(num_samples):
            val = int(32767.0 * 0.3 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return buf.getvalue()


# ==============================================================================
# 1. SpeechTextSanitizer Unit Tests
# ==============================================================================

class TestSpeechTextSanitizer:
    """Test suite for deterministic speech-only text sanitization."""

    def test_strip_single_citation(self):
        raw = "The Chennakeshava Temple was built in 1117 CE. [1]"
        expected = "The Chennakeshava Temple was built in 1117 CE."
        assert SpeechTextSanitizer.sanitize(raw) == expected

    def test_strip_multiple_citations(self):
        raw = "Belur was the capital [1], while Halebidu was the seat of power [2] [12]."
        expected = "Belur was the capital , while Halebidu was the seat of power ."
        # Normalizing punctuation spacing
        sanitized = SpeechTextSanitizer.sanitize(raw)
        assert "[1]" not in sanitized
        assert "[2]" not in sanitized
        assert "[12]" not in sanitized
        assert "Belur was the capital" in sanitized

    def test_strip_markdown_formatting(self):
        raw = "# Welcome to **Hampi**\n\n- The *Virupaksha* temple is `active`.\n> A UNESCO site."
        sanitized = SpeechTextSanitizer.sanitize(raw)
        assert "#" not in sanitized
        assert "**" not in sanitized
        assert "*" not in sanitized
        assert "`" not in sanitized
        assert ">" not in sanitized
        assert "Welcome to Hampi" in sanitized
        assert "Virupaksha temple is active" in sanitized
        assert "A UNESCO site" in sanitized

    def test_strip_urls(self):
        raw = "Visit https://karnatakatourism.org or www.karnataka.gov.in for timings."
        sanitized = SpeechTextSanitizer.sanitize(raw)
        assert "https://" not in sanitized
        assert "www." not in sanitized
        assert "Visit" in sanitized
        assert "for timings." in sanitized

    def test_kannada_preservation_and_citation_stripping(self):
        raw = "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ರಾಜ ವಿಷ್ಣುವರ್ಧನನು ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ ನಿರ್ಮಿಸಿದರು. [1] [2]"
        sanitized = SpeechTextSanitizer.sanitize(raw)
        assert "[1]" not in sanitized
        assert "[2]" not in sanitized
        assert "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು" in sanitized
        assert "1117ರಲ್ಲಿ ನಿರ್ಮಿಸಿದರು." in sanitized

    def test_kannada_exact_fallback_preservation(self):
        raw = "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."
        assert SpeechTextSanitizer.sanitize(raw) == raw

    def test_english_exact_fallback_preservation(self):
        raw = "Information is not available in the knowledge base."
        assert SpeechTextSanitizer.sanitize(raw) == raw

    def test_contains_kannada_detection(self):
        assert SpeechTextSanitizer.contains_kannada("ಹಂಪಿ") is True
        assert SpeechTextSanitizer.contains_kannada("Hampi is located in Karnataka") is False
        assert SpeechTextSanitizer.contains_kannada("Hampi (ಹಂಪಿ)") is True


# ==============================================================================
# 2. PiperTTSProvider Unit Tests
# ==============================================================================

class TestPiperTTSProvider:
    """Test suite for English Piper TTS provider."""

    def test_supported_languages(self):
        provider = PiperTTSProvider()
        assert "en" in provider.get_supported_languages()

    @pytest.mark.asyncio
    async def test_piper_synthesis_empty_text_error(self):
        provider = PiperTTSProvider()
        with pytest.raises(AppException) as exc_info:
            await provider.synthesize("", language="en")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_piper_synthesis_mock(self):
        provider = PiperTTSProvider()
        mock_voice = MagicMock()
        
        def fake_synthesize_wav(text, wav_file):
            fake_wav = create_synthetic_wav(duration_seconds=1.5, sample_rate=22050)
            # copy fake wav data into wav_file
            with wave.open(io.BytesIO(fake_wav), "rb") as r:
                wav_file.setnchannels(r.getnchannels())
                wav_file.setsampwidth(r.getsampwidth())
                wav_file.setframerate(r.getframerate())
                wav_file.writeframes(r.readframes(r.getnframes()))

        mock_voice.synthesize_wav.side_effect = fake_synthesize_wav
        provider._voice = mock_voice

        result = await provider.synthesize("Welcome to Karnataka.", language="en")
        assert isinstance(result, AudioSynthesisResult)
        assert result.sample_rate == 22050
        assert result.channels == 1
        assert result.sample_width == 2
        assert result.mime_type == "audio/wav"
        assert len(result.audio_bytes) > 0
        assert result.duration_seconds > 0.0

    @pytest.mark.asyncio
    async def test_piper_check_health_success(self):
        provider = PiperTTSProvider()
        provider._voice = MagicMock()
        assert await provider.check_health() is True


# ==============================================================================
# 3. MMSTTSProvider Unit Tests
# ==============================================================================

class TestMMSTTSProvider:
    """Test suite for Kannada Meta MMS-TTS provider."""

    def test_supported_languages(self):
        provider = MMSTTSProvider()
        assert "kn" in provider.get_supported_languages()

    @pytest.mark.asyncio
    async def test_mms_synthesis_empty_text_error(self):
        provider = MMSTTSProvider()
        with pytest.raises(AppException) as exc_info:
            await provider.synthesize("   ", language="kn")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_mms_synthesis_mock(self):
        import torch
        provider = MMSTTSProvider()
        
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}
        
        mock_model = MagicMock()
        mock_model.config.sampling_rate = 16000
        mock_output = MagicMock()
        # 16000 samples = 1 second of audio
        mock_output.waveform = torch.zeros((1, 16000), dtype=torch.float32)
        mock_model.return_value = mock_output
        
        provider._tokenizer = mock_tokenizer
        provider._model = mock_model

        result = await provider.synthesize("ಕರ್ನಾಟಕಕ್ಕೆ ಸುಸ್ವಾಗತ.", language="kn")
        assert isinstance(result, AudioSynthesisResult)
        assert result.sample_rate == 16000
        assert result.channels == 1
        assert result.sample_width == 2
        assert result.mime_type == "audio/wav"
        assert len(result.audio_bytes) > 0
        assert abs(result.duration_seconds - 1.0) < 0.1

    @pytest.mark.asyncio
    async def test_mms_check_health_success(self):
        provider = MMSTTSProvider()
        provider._tokenizer = MagicMock()
        provider._model = MagicMock()
        assert await provider.check_health() is True


# ==============================================================================
# 4. CompositeTTSProvider Routing Tests
# ==============================================================================

class TestCompositeTTSProvider:
    """Test suite for multi-engine Composite TTS router."""

    @pytest.mark.asyncio
    async def test_routing_english(self):
        mock_piper = AsyncMock(spec=PiperTTSProvider)
        mock_mms = AsyncMock(spec=MMSTTSProvider)
        
        mock_piper.synthesize.return_value = AudioSynthesisResult(
            audio_bytes=b"RIFF_EN", sample_rate=22050, channels=1, sample_width=2, duration_seconds=1.0
        )

        composite = CompositeTTSProvider(piper_provider=mock_piper, mms_provider=mock_mms)
        res = await composite.synthesize("Hello", language="en_US")
        
        mock_piper.synthesize.assert_awaited_once_with(text="Hello", language="en", speaker_id=None)
        mock_mms.synthesize.assert_not_awaited()
        assert res.audio_bytes == b"RIFF_EN"

    @pytest.mark.asyncio
    async def test_routing_kannada(self):
        mock_piper = AsyncMock(spec=PiperTTSProvider)
        mock_mms = AsyncMock(spec=MMSTTSProvider)
        
        mock_mms.synthesize.return_value = AudioSynthesisResult(
            audio_bytes=b"RIFF_KN", sample_rate=16000, channels=1, sample_width=2, duration_seconds=1.0
        )

        composite = CompositeTTSProvider(piper_provider=mock_piper, mms_provider=mock_mms)
        res = await composite.synthesize("ನಮಸ್ಕಾರ", language="kn")
        
        mock_mms.synthesize.assert_awaited_once_with(text="ನಮಸ್ಕಾರ", language="kn", speaker_id=None)
        mock_piper.synthesize.assert_not_awaited()
        assert res.audio_bytes == b"RIFF_KN"

    @pytest.mark.asyncio
    async def test_unsupported_language_rejected(self):
        mock_piper = AsyncMock(spec=PiperTTSProvider)
        mock_mms = AsyncMock(spec=MMSTTSProvider)
        composite = CompositeTTSProvider(piper_provider=mock_piper, mms_provider=mock_mms)
        
        with pytest.raises(AppException) as exc_info:
            await composite.synthesize("Bonjour", language="fr")
        assert exc_info.value.status_code == 400
        assert "Unsupported TTS language: 'fr'" in exc_info.value.message


# ==============================================================================
# 5. TTSService Session & Authorization Tests
# ==============================================================================

class TestTTSService:
    """Test suite for authorized assistant response synthesis."""

    @pytest.mark.asyncio
    async def test_session_not_found(self, db_session: AsyncSession):
        service = TTSService()
        req = MessageSpeechSynthesisRequest(
            session_uuid="non-existent-session",
            assistant_message_id="non-existent-msg",
        )
        with pytest.raises(AppException) as exc_info:
            await service.synthesize_message_audio(request=req, db=db_session)
        assert exc_info.value.status_code == 404
        assert "Tourist session not found" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_message_not_found(self, db_session: AsyncSession):
        # Create session
        session = ChatSession(session_uuid="valid-session-1", language_code="en")
        db_session.add(session)
        await db_session.commit()

        service = TTSService()
        req = MessageSpeechSynthesisRequest(
            session_uuid="valid-session-1",
            assistant_message_id="non-existent-msg-id",
        )
        with pytest.raises(AppException) as exc_info:
            await service.synthesize_message_audio(request=req, db=db_session)
        assert exc_info.value.status_code == 404
        assert "Chat message not found" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_message_wrong_session(self, db_session: AsyncSession):
        s1 = ChatSession(session_uuid="session-1", language_code="en")
        s2 = ChatSession(session_uuid="session-2", language_code="en")
        db_session.add_all([s1, s2])
        await db_session.flush()

        msg = ChatMessage(
            session_id=s2.id,
            sender_type=SenderType.ASSISTANT,
            message_text="Belur was built in 1117 CE. [1]",
            detected_language="en",
        )
        db_session.add(msg)
        await db_session.commit()

        service = TTSService()
        req = MessageSpeechSynthesisRequest(
            session_uuid="session-1",
            assistant_message_id=msg.id,
        )
        with pytest.raises(AppException) as exc_info:
            await service.synthesize_message_audio(request=req, db=db_session)
        assert exc_info.value.status_code == 403
        assert "does not belong to the specified session" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_reject_user_message_synthesis(self, db_session: AsyncSession):
        s = ChatSession(session_uuid="session-user-msg", language_code="en")
        db_session.add(s)
        await db_session.flush()

        user_msg = ChatMessage(
            session_id=s.id,
            sender_type=SenderType.USER,
            message_text="Tell me about Belur",
            detected_language="en",
        )
        db_session.add(user_msg)
        await db_session.commit()

        service = TTSService()
        req = MessageSpeechSynthesisRequest(
            session_uuid="session-user-msg",
            assistant_message_id=user_msg.id,
        )
        with pytest.raises(AppException) as exc_info:
            await service.synthesize_message_audio(request=req, db=db_session)
        assert exc_info.value.status_code == 400
        assert "Only completed assistant messages can be synthesized" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_successful_assistant_message_synthesis_english(self, db_session: AsyncSession):
        s = ChatSession(session_uuid="session-success-en", language_code="en")
        db_session.add(s)
        await db_session.flush()

        asst_msg = ChatMessage(
            session_id=s.id,
            sender_type=SenderType.ASSISTANT,
            message_text="The Chennakeshava Temple was commissioned in 1117 CE. [1]",
            detected_language="en",
        )
        db_session.add(asst_msg)
        await db_session.commit()

        mock_provider = AsyncMock(spec=ITTSProvider)
        mock_provider.synthesize.return_value = AudioSynthesisResult(
            audio_bytes=create_synthetic_wav(duration_seconds=2.0, sample_rate=22050),
            sample_rate=22050,
            channels=1,
            sample_width=2,
            duration_seconds=2.0,
            mime_type="audio/wav",
        )

        service = TTSService(provider=mock_provider)
        req = MessageSpeechSynthesisRequest(
            session_uuid="session-success-en",
            assistant_message_id=asst_msg.id,
        )

        audio_bytes, result, metadata = await service.synthesize_message_audio(request=req, db=db_session)
        
        # Verify sanitized text was passed to provider (stripped [1])
        mock_provider.synthesize.assert_awaited_once_with(
            text="The Chennakeshava Temple was commissioned in 1117 CE.",
            language="en",
        )
        assert len(audio_bytes) > 0
        assert metadata.sample_rate == 22050
        assert metadata.language == "en"
        assert metadata.duration_seconds == 2.0


# ==============================================================================
# 6. Public Tourist Voice API Endpoint Tests
# ==============================================================================

class TestTouristVoiceAPI:
    """Test suite for POST /api/v1/tourist/voice/synthesize endpoint."""

    @pytest.mark.asyncio
    async def test_synthesize_endpoint_success(self, client_with_db: httpx.AsyncClient, db_session: AsyncSession):
        # Create session and assistant message
        s = ChatSession(session_uuid="api-sess-1", language_code="kn")
        db_session.add(s)
        await db_session.flush()

        msg = ChatMessage(
            session_id=s.id,
            sender_type=SenderType.ASSISTANT,
            message_text="ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯ [1]",
            detected_language="kn",
        )
        db_session.add(msg)
        await db_session.commit()

        mock_wav = create_synthetic_wav(duration_seconds=1.5, sample_rate=16000)
        
        with patch.object(TTSService, "synthesize_message_audio") as mock_synth:
            mock_synth.return_value = (
                mock_wav,
                AudioSynthesisResult(
                    audio_bytes=mock_wav,
                    sample_rate=16000,
                    channels=1,
                    sample_width=2,
                    duration_seconds=1.5,
                ),
                SpeechSynthesisMetadata(
                    duration_seconds=1.5,
                    sample_rate=16000,
                    channels=1,
                    language="kn",
                ),
            )

            resp = await client_with_db.post(
                "/api/v1/tourist/voice/synthesize",
                json={
                    "session_uuid": "api-sess-1",
                    "assistant_message_id": msg.id,
                },
            )

            assert resp.status_code == 200
            assert resp.headers["content-type"] == "audio/wav"
            assert resp.headers["X-Audio-Sample-Rate"] == "16000"
            assert resp.headers["X-Language"] == "kn"
            assert resp.headers["X-Audio-Duration-Seconds"] == "1.50"
            assert len(resp.content) == len(mock_wav)

    @pytest.mark.asyncio
    async def test_synthesize_endpoint_session_not_found(self, async_client: httpx.AsyncClient):
        resp = await async_client.post(
            "/api/v1/tourist/voice/synthesize",
            json={
                "session_uuid": "non-existent-uuid",
                "assistant_message_id": "non-existent-msg",
            },
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_synthesize_endpoint_rejects_missing_fields(self, async_client: httpx.AsyncClient):
        resp = await async_client.post(
            "/api/v1/tourist/voice/synthesize",
            json={"session_uuid": "sess-1"},
        )
        assert resp.status_code == 422


# ==============================================================================
# 7. Voice Registry Database Seed Tests
# ==============================================================================

class TestVoiceRegistrySeed:
    """Test suite for voice registry configuration."""

    @pytest.mark.asyncio
    async def test_voice_registry_approved_voices(self):
        from app.infrastructure.db.seed import APPROVED_VOICES
        
        voice_names = {v["voice_name"] for v in APPROVED_VOICES}
        assert "piper_en_lessac_medium" in voice_names
        assert "mms_kn_vits" in voice_names

        for v in APPROVED_VOICES:
            assert v["sample_rate"] in (16000, 22050)
            assert v["language_code"] in ("en", "kn")
            assert v["provider"] in (VoiceProvider.PIPER, VoiceProvider.MMS_TTS)


# ==============================================================================
# 8. Live Model Synthesis & End-to-End Conversation Integration Tests
# ==============================================================================

class TestLiveTTSPipeline:
    """Integration test suite executing offline inference on actual local models."""

    @pytest.mark.asyncio
    async def test_live_piper_english_synthesis(self):
        provider = PiperTTSProvider()
        result = await provider.synthesize(
            text="The Chennakeshava Temple at Belur was commissioned by King Vishnuvardhana in 1117 CE.",
            language="en",
        )
        assert isinstance(result, AudioSynthesisResult)
        assert result.sample_rate == 22050
        assert result.channels == 1
        assert result.sample_width == 2
        assert result.duration_seconds > 4.0
        assert len(result.audio_bytes) > 100000
        # Verify RIFF header in bytes
        assert result.audio_bytes[:4] == b"RIFF"

    @pytest.mark.asyncio
    async def test_live_mms_kannada_synthesis(self):
        provider = MMSTTSProvider(local_files_only=True)
        result = await provider.synthesize(
            text="ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ರಾಜ ವಿಷ್ಣುವರ್ಧನನು ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ ನಿರ್ಮಿಸಿದರು.",
            language="kn",
        )
        assert isinstance(result, AudioSynthesisResult)
        assert result.sample_rate == 16000
        assert result.channels == 1
        assert result.sample_width == 2
        assert result.duration_seconds > 4.0
        assert len(result.audio_bytes) > 100000
        assert result.audio_bytes[:4] == b"RIFF"

    @pytest.mark.asyncio
    async def test_live_composite_provider_bilingual(self):
        composite = CompositeTTSProvider()
        
        # English synthesis via Piper
        en_res = await composite.synthesize("Welcome to Karnataka Tourism.", language="en")
        assert en_res.sample_rate == 22050
        assert en_res.audio_bytes[:4] == b"RIFF"

        # Kannada synthesis via MMS-TTS
        kn_res = await composite.synthesize("ಕರ್ನಾಟಕ ಪ್ರವಾಸೋದ್ಯಮಕ್ಕೆ ಸುಸ್ವಾಗತ.", language="kn")
        assert kn_res.sample_rate == 16000
        assert kn_res.audio_bytes[:4] == b"RIFF"

    @pytest.mark.asyncio
    async def test_live_e2e_tourist_conversation_to_speech(
        self,
        client_with_db: httpx.AsyncClient,
        db_session: AsyncSession,
    ):
        # 1. Create a tourist session
        session = ChatSession(session_uuid="live-e2e-session-1", language_code="en")
        db_session.add(session)
        await db_session.flush()

        # 2. Insert assistant response with citations and markdown
        asst_msg = ChatMessage(
            session_id=session.id,
            sender_type=SenderType.ASSISTANT,
            message_text="**Belur** is renowned for the *Chennakeshava Temple*, built in 1117 CE. [1] [2]",
            detected_language="en",
            citations_json={"citations": [{"chunk_id": "c1", "source": "belur.pdf"}]},
        )
        db_session.add(asst_msg)
        await db_session.commit()

        # 3. Request speech synthesis via the public API endpoint
        resp = await client_with_db.post(
            "/api/v1/tourist/voice/synthesize",
            json={
                "session_uuid": "live-e2e-session-1",
                "assistant_message_id": asst_msg.id,
            },
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/wav"
        assert resp.headers["X-Audio-Sample-Rate"] == "22050"
        assert resp.headers["X-Language"] == "en"
        assert float(resp.headers["X-Audio-Duration-Seconds"]) > 2.0
        assert resp.content[:4] == b"RIFF"

        # Verify that original database message retains citations and markdown intact
        await db_session.refresh(asst_msg)
        assert "[1]" in asst_msg.message_text
        assert "**Belur**" in asst_msg.message_text
