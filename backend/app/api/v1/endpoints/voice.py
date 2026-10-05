"""
Public, unauthenticated tourist speech-to-text (STT), voice conversation, and text-to-speech (TTS) endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.application.speech.schemas import (
    MessageSpeechSynthesisRequest,
    TranscriptionResponse,
    VoiceChatResponse,
)
from app.application.speech.stt_service import SpeechToTextService
from app.application.speech.tts_service import TTSService
from app.infrastructure.db.session import get_db_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/tourist", tags=["Public Tourist Voice"])


@router.post(
    "/voice/transcribe",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe tourist audio recording (STT)",
    description="Transcribes an uploaded audio recording (WAV, MP3, WebM, OGG, M4A) using local offline Faster-Whisper. Audio is transient and never stored permanently.",
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio recording file buffer (WAV, MP3, WebM, OGG, M4A)"),
    language: Optional[str] = Form(None, description="Optional language code hint (e.g. 'kn' or 'en')"),
) -> TranscriptionResponse:
    """
    Public anonymous endpoint for audio transcription using Faster-Whisper.
    """
    service = SpeechToTextService()
    return await service.transcribe(upload_file=file, language=language)


@router.post(
    "/chat/voice",
    response_model=VoiceChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Voice chat conversational turn (STT + RAG + LLM)",
    description="Transcribes tourist speech and pipes the transcribed query into the grounded conversation engine, returning both the transcript and grounded answer with citations.",
)
async def voice_chat_turn(
    session_uuid: str = Form(..., description="Active tourist chat session UUID"),
    file: UploadFile = File(..., description="Audio recording file buffer"),
    language: Optional[str] = Form(None, description="Optional language code hint"),
    db: AsyncSession = Depends(get_db_session),
) -> VoiceChatResponse:
    """
    End-to-end voice-to-chat conversational turn: Speech -> STT -> RAG -> Ollama -> Response.
    """
    service = SpeechToTextService()
    return await service.voice_chat(
        upload_file=file,
        session_uuid=session_uuid,
        session=db,
        language=language,
    )


@router.post(
    "/voice/synthesize",
    status_code=status.HTTP_200_OK,
    summary="Synthesize speech audio for approved assistant response (TTS)",
    description="Synthesizes in-memory 16-bit PCM WAV audio for a completed, authoritative ASSISTANT message in an active tourist session. Visible answer text and citations remain intact; speech text is sanitized.",
    responses={
        200: {
            "content": {"audio/wav": {}},
            "description": "Synthesized 16-bit PCM WAV audio stream.",
        },
        400: {"description": "Invalid message state or empty synthesizable content."},
        403: {"description": "Message does not belong to the session."},
        404: {"description": "Tourist session or message not found."},
    },
)
async def synthesize_speech(
    request: MessageSpeechSynthesisRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Synthesizes speech audio for an authorized assistant response.
    English uses Piper TTS (22.05 kHz); Kannada uses Meta MMS-TTS (16.0 kHz).
    """
    service = TTSService()
    audio_bytes, result, metadata = await service.synthesize_message_audio(request=request, db=db)

    headers = {
        "Content-Disposition": 'inline; filename="assistant_response.wav"',
        "X-Audio-Duration-Seconds": f"{metadata.duration_seconds:.2f}",
        "X-Audio-Sample-Rate": str(metadata.sample_rate),
        "X-Audio-Channels": str(metadata.channels),
        "X-Language": metadata.language,
    }

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers=headers,
    )
