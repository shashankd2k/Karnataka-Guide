"""
Application service for Text-To-Speech (TTS) speech synthesis.
Coordinates text sanitization, session validation, message ownership verification,
and offline audio rendering via CompositeTTSProvider.
"""

import re
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.application.speech.schemas import MessageSpeechSynthesisRequest, SpeechSynthesisMetadata
from app.core.errors import AppException, BadRequestException, ForbiddenException, NotFoundException
from app.domain.ports.tts import AudioSynthesisResult, ITTSProvider
from app.infrastructure.db.models.chat import ChatMessage, ChatSession, SenderType
from app.infrastructure.tts.composite import CompositeTTSProvider

logger = structlog.get_logger(__name__)

# Regular expressions for deterministic speech text sanitization
_CITATION_PATTERN = re.compile(r"\[\s*\d+\s*\]")
_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
_MD_BOLD_ASTERISK = re.compile(r"\*\*([^*]+)\*\*")
_MD_ITALIC_ASTERISK = re.compile(r"\*([^*]+)\*")
_MD_BOLD_UNDERSCORE = re.compile(r"__([^_]+)__")
_MD_ITALIC_UNDERSCORE = re.compile(r"_([^_]+)_")
_MD_CODE_BLOCK = re.compile(r"```[\s\S]*?```")
_MD_INLINE_CODE = re.compile(r"`([^`]+)`")
_MD_HEADER = re.compile(r"^#+\s*", re.MULTILINE)
_MD_BLOCKQUOTE = re.compile(r"^>\s*", re.MULTILINE)
_MD_LIST_BULLET = re.compile(r"^[\s*+-]+\s+", re.MULTILINE)
_EXTRA_WHITESPACE = re.compile(r"\s+")
_KANNADA_UNICODE = re.compile(r"[\u0C80-\u0CFF]")


class SpeechTextSanitizer:
    """
    Deterministic text sanitizer for speech rendering.
    Strips citation markers, markdown formatting, raw URLs, and control characters
    without altering original database content or display metadata.
    """

    @classmethod
    def sanitize(cls, text: str) -> str:
        if not text:
            return ""

        s = text
        # 1. Remove code blocks and inline code
        s = _MD_CODE_BLOCK.sub(" ", s)
        s = _MD_INLINE_CODE.sub(r"\1", s)

        # 2. Strip bracketed numeric citations (e.g. [1], [2], [ 12 ])
        s = _CITATION_PATTERN.sub(" ", s)

        # 3. Strip URLs
        s = _URL_PATTERN.sub(" ", s)

        # 4. Strip markdown formatting
        s = _MD_BOLD_ASTERISK.sub(r"\1", s)
        s = _MD_ITALIC_ASTERISK.sub(r"\1", s)
        s = _MD_BOLD_UNDERSCORE.sub(r"\1", s)
        s = _MD_ITALIC_UNDERSCORE.sub(r"\1", s)
        s = _MD_HEADER.sub("", s)
        s = _MD_BLOCKQUOTE.sub("", s)
        s = _MD_LIST_BULLET.sub("", s)

        # 5. Remove any leftover markdown characters (*, _, #, ~, `)
        s = re.sub(r"[*_#~`]", "", s)

        # 6. Normalize whitespace
        s = _EXTRA_WHITESPACE.sub(" ", s).strip()
        return s

    @classmethod
    def contains_kannada(cls, text: str) -> bool:
        """Check if text contains Kannada Unicode codepoints."""
        return bool(_KANNADA_UNICODE.search(text))


class TTSService:
    """
    Application-layer service coordinating offline speech synthesis.
    Enforces the security rule that only completed server-approved assistant messages
    can be synthesized into speech.
    """

    def __init__(self, provider: Optional[ITTSProvider] = None) -> None:
        self.provider = provider or CompositeTTSProvider()
        self.sanitizer = SpeechTextSanitizer()

    async def synthesize_message_audio(
        self,
        request: MessageSpeechSynthesisRequest,
        db: AsyncSession,
    ) -> tuple[bytes, AudioSynthesisResult, SpeechSynthesisMetadata]:
        """
        Synthesize audio for an approved assistant response message.
        
        Steps:
        1. Validate tourist session exists.
        2. Validate message exists, belongs to the session, and has sender_type == ASSISTANT.
        3. Determine target language ('kn' if contains Kannada or session/msg is kn, else 'en').
        4. Clean text with SpeechTextSanitizer.
        5. Invoke CompositeTTSProvider offline synthesis.
        6. Return raw WAV bytes and synthesis metadata.
        """
        # Step 1: Validate session
        session_stmt = select(ChatSession).where(ChatSession.session_uuid == request.session_uuid)
        session_res = await db.execute(session_stmt)
        session = session_res.scalar_one_or_none()
        if not session:
            raise NotFoundException(
                message=f"Tourist session not found: '{request.session_uuid}'",
            )

        # Step 2: Fetch message and verify ownership
        msg_stmt = select(ChatMessage).where(ChatMessage.id == request.assistant_message_id)
        msg_res = await db.execute(msg_stmt)
        message = msg_res.scalar_one_or_none()
        if not message:
            raise NotFoundException(
                message=f"Chat message not found: '{request.assistant_message_id}'",
            )

        if message.session_id != session.id:
            raise ForbiddenException(
                message="Chat message does not belong to the specified session.",
            )

        if message.sender_type != SenderType.ASSISTANT:
            raise BadRequestException(
                message="Only completed assistant messages can be synthesized into speech.",
            )

        # Step 3: Determine authoritative language
        lang = (message.detected_language or session.language_code or "en").lower().strip()
        if self.sanitizer.contains_kannada(message.message_text):
            lang = "kn"
        elif lang not in {"en", "kn"}:
            lang = "en"

        # Step 4: Sanitize text for speech
        speech_text = self.sanitizer.sanitize(message.message_text)
        if not speech_text:
            raise AppException(
                status_code=400,
                message="Assistant message does not contain any synthesizable speech content.",
            )

        # Step 5: Synthesize via CompositeTTSProvider
        logger.info(
            "Synthesizing assistant response audio",
            session_uuid=request.session_uuid,
            message_id=request.assistant_message_id,
            language=lang,
            raw_len=len(message.message_text),
            speech_len=len(speech_text),
        )

        result = await self.provider.synthesize(text=speech_text, language=lang)

        metadata = SpeechSynthesisMetadata(
            duration_seconds=result.duration_seconds,
            sample_rate=result.sample_rate,
            channels=result.channels,
            language=lang,
            mime_type=result.mime_type,
        )

        return result.audio_bytes, result, metadata

    async def synthesize_direct(
        self,
        text: str,
        language: str = "en",
    ) -> tuple[bytes, AudioSynthesisResult]:
        """
        Internal / testing method to sanitize and synthesize text directly.
        """
        speech_text = self.sanitizer.sanitize(text)
        if not speech_text:
            raise AppException(status_code=400, message="Text contains no synthesizable content.")

        lang = language.lower().strip() if language else "en"
        if self.sanitizer.contains_kannada(speech_text):
            lang = "kn"

        result = await self.provider.synthesize(text=speech_text, language=lang)
        return result.audio_bytes, result

    async def check_health(self) -> bool:
        """Check health of underlying TTS providers."""
        return await self.provider.check_health()

    def get_supported_languages(self) -> List[str]:
        return self.provider.get_supported_languages()
