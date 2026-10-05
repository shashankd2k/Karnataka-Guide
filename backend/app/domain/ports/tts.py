"""
Domain port for Text-To-Speech (TTS) speech synthesis engines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class AudioSynthesisResult:
    """Structured synthesis result output from a TTS engine."""
    audio_bytes: bytes
    sample_rate: int
    channels: int
    sample_width: int
    duration_seconds: float
    mime_type: str = "audio/wav"


class ITTSProvider(ABC):
    """
    Abstract domain port declaring the contract for offline TTS providers.
    Decouples application speech orchestration from concrete synthesis engines (Piper TTS / Meta MMS-TTS).
    """

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        language: str,
        speaker_id: Optional[str] = None,
    ) -> AudioSynthesisResult:
        """
        Synthesize speech audio from text asynchronously.

        Args:
            text: Sanitized text content to synthesize.
            language: Target ISO language code ('en' or 'kn').
            speaker_id: Optional speaker voice profile ID.

        Returns:
            Structured AudioSynthesisResult containing in-memory WAV bytes and audio metadata.
        """
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """
        Check if the TTS provider models and runtimes are initialized and healthy.

        Returns:
            True if healthy and ready for inference, False otherwise.
        """
        pass

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """
        List of ISO-639 language codes supported by this TTS provider.
        """
        pass
