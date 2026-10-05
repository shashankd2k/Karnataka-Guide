"""
Domain ports package exports.
"""

from app.domain.ports.llm import ILLMProvider
from app.domain.ports.stt import (
    ISpeechToTextProvider,
    TranscriptionResult,
    TranscriptionSegment,
)
from app.domain.ports.translation import ITranslationProvider
from app.domain.ports.tts import AudioSynthesisResult, ITTSProvider

__all__ = [
    "AudioSynthesisResult",
    "ILLMProvider",
    "ISpeechToTextProvider",
    "ITranslationProvider",
    "ITTSProvider",
    "TranscriptionResult",
    "TranscriptionSegment",
]
