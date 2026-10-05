"""
Domain port for Speech-To-Text (STT) transcription engines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class TranscriptionSegment:
    """Individual timestamped transcription segment."""
    start: float
    end: float
    text: str
    avg_logprob: float = 0.0
    no_speech_prob: float = 0.0


@dataclass(frozen=True)
class TranscriptionResult:
    """Structured transcription result output from an STT engine."""
    text: str
    language: str
    language_probability: float
    duration_seconds: float
    segments: List[TranscriptionSegment] = field(default_factory=list)


class ISpeechToTextProvider(ABC):
    """
    Abstract domain port declaring the contract for local/quantized STT providers.
    Decouples application speech orchestration from concrete transcription engines (Faster-Whisper).
    """

    @abstractmethod
    async def transcribe_audio(
        self,
        file_path: Path,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe an audio file asynchronously.

        Args:
            file_path: Path to the validated local audio file.
            language: Optional language code hint (e.g. 'kn' or 'en'). Auto-detected if None.

        Returns:
            Structured TranscriptionResult containing transcript text, detected language, and metadata.
        """
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """
        Check if the STT engine and local models are initialized and ready for inference.

        Returns:
            True if engine is healthy and operational, False otherwise.
        """
        pass
