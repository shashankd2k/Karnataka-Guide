"""
Pydantic v2 schemas for Speech-To-Text (STT), Text-To-Speech (TTS), and Voice Conversational APIs.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.application.conversation.schemas import ChatTurnResponse


class TranscriptionSegmentSchema(BaseModel):
    """Timestamped transcription segment for subtitles or synchronized audio."""
    start: float = Field(..., description="Start timestamp in seconds")
    end: float = Field(..., description="End timestamp in seconds")
    text: str = Field(..., description="Transcribed text for this segment")

    model_config = ConfigDict(from_attributes=True)


class TranscriptionResponse(BaseModel):
    """Structured transcription output contract."""
    text: str = Field(..., description="Full transcribed speech text")
    language: str = Field(..., description="Detected or requested language code (e.g. 'kn' or 'en')")
    language_probability: float = Field(..., description="Model confidence score for the detected language")
    duration_seconds: float = Field(..., description="Total duration of the processed audio in seconds")
    segments: List[TranscriptionSegmentSchema] = Field(default_factory=list, description="Timestamped segments")

    model_config = ConfigDict(from_attributes=True)


class VoiceChatResponse(BaseModel):
    """Combined voice transcription and conversational response contract."""
    transcription: TranscriptionResponse = Field(..., description="Speech-to-text transcription result")
    chat: ChatTurnResponse = Field(..., description="Grounded tourist conversational answer and citations")

    model_config = ConfigDict(from_attributes=True)


class MessageSpeechSynthesisRequest(BaseModel):
    """Request contract to synthesize an authoritative assistant response."""
    session_uuid: str = Field(..., description="Tourist anonymous session UUID")
    assistant_message_id: str = Field(..., description="UUID of the completed ASSISTANT chat message to synthesize")


class SpeechSynthesisMetadata(BaseModel):
    """Metadata describing generated audio waveform."""
    duration_seconds: float = Field(..., description="Audio length in seconds")
    sample_rate: int = Field(..., description="Sampling rate in Hz (e.g. 22050 or 16000)")
    channels: int = Field(default=1, description="Audio channels (1 = Mono)")
    language: str = Field(..., description="Spoken language ISO code ('en' or 'kn')")
    mime_type: str = Field(default="audio/wav", description="Audio MIME type")
