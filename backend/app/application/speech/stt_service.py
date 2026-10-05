"""
Application service for Speech-To-Text (STT) and voice-enabled conversational flows.
Coordinates multi-layer validation, temporary file lifecycle, transcription, and RAG execution.
"""

from typing import Optional
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.application.conversation.service import ConversationService
from app.application.speech.schemas import (
    TranscriptionResponse,
    TranscriptionSegmentSchema,
    VoiceChatResponse,
)
from app.domain.ports.stt import ISpeechToTextProvider, TranscriptionResult
from app.infrastructure.stt.audio_validator import (
    AudioValidationError,
    temp_audio_file_context,
)
from app.infrastructure.stt.faster_whisper import FasterWhisperProvider

logger = structlog.get_logger(__name__)


ALLOWED_STT_LANGUAGES = {"en", "kn"}


class SpeechToTextService:
    """
    Coordinates speech ingestion, validation, transcription, and voice chat piping.
    """

    def __init__(self, provider: Optional[ISpeechToTextProvider] = None):
        self.provider = provider or FasterWhisperProvider()

    @staticmethod
    def _sanitize_language_hint(language: Optional[str]) -> Optional[str]:
        """Validate language hint against allowed codes ('en', 'kn')."""
        if not language:
            return None
        lang = language.strip().lower()
        return lang if lang in ALLOWED_STT_LANGUAGES else None

    async def transcribe(
        self,
        upload_file: UploadFile,
        language: Optional[str] = None,
    ) -> TranscriptionResponse:
        """
        Validate, decode, transcribe an audio upload, and ensure temporary file deletion.
        """
        safe_lang = self._sanitize_language_hint(language)
        async with temp_audio_file_context(upload_file) as temp_path:
            result: TranscriptionResult = await self.provider.transcribe_audio(
                file_path=temp_path,
                language=safe_lang,
            )

            segments = [
                TranscriptionSegmentSchema(
                    start=round(seg.start, 2),
                    end=round(seg.end, 2),
                    text=seg.text,
                )
                for seg in result.segments
            ]

            return TranscriptionResponse(
                text=result.text,
                language=result.language,
                language_probability=round(result.language_probability, 4),
                duration_seconds=round(result.duration_seconds, 2),
                segments=segments,
            )

    async def voice_chat(
        self,
        upload_file: UploadFile,
        session_uuid: str,
        session: AsyncSession,
        language: Optional[str] = None,
    ) -> VoiceChatResponse:
        """
        Transcribe user voice recording and pipe the transcribed text into the
        existing ConversationService RAG pipeline.
        """
        conv_service = ConversationService(session=session)
        chat_session = await conv_service.get_session_by_uuid(session_uuid)

        # Prefer trusted session language if established, fallback to sanitized client hint
        effective_language = self._sanitize_language_hint(language)
        if chat_session.language_code in ALLOWED_STT_LANGUAGES:
            effective_language = chat_session.language_code

        # 1. Transcribe audio upload
        transcription = await self.transcribe(upload_file=upload_file, language=effective_language)

        if not transcription.text.strip():
            raise AudioValidationError(
                "No audible speech detected in the uploaded recording.",
                details={"duration_seconds": transcription.duration_seconds},
            )

        # 2. Pipe recognized speech to the existing ConversationService
        chat_turn = await conv_service.process_turn(
            session_uuid=session_uuid,
            user_message=transcription.text,
        )

        return VoiceChatResponse(
            transcription=transcription,
            chat=chat_turn,
        )
