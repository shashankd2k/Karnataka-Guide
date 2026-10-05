"""
Faster-Whisper infrastructure provider implementing the ISpeechToTextProvider domain port.
Runs local, quantized CTranslate2 speech recognition models on CPU with non-blocking async execution.
"""

import asyncio
from pathlib import Path
import threading
import time
from typing import List, Optional

from faster_whisper import WhisperModel
import structlog

from app.core.config import Settings, get_settings
from app.core.errors import AppException
from app.domain.ports.stt import (
    ISpeechToTextProvider,
    TranscriptionResult,
    TranscriptionSegment,
)

logger = structlog.get_logger(__name__)


class TranscriptionError(AppException):
    """Raised when audio transcription fails during model decoding."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            code="TRANSCRIPTION_FAILED",
            status_code=500,
            details=details or {},
        )


class ModelUnavailableError(AppException):
    """Raised when the Whisper model cannot be loaded or initialized."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            code="STT_MODEL_UNAVAILABLE",
            status_code=503,
            details=details or {},
        )


class FasterWhisperProvider(ISpeechToTextProvider):
    """
    Asynchronous Faster-Whisper provider with process-level model singleton caching.
    Uses CTranslate2 execution under an async thread executor to avoid blocking the event loop.
    """

    _model_instance: Optional[WhisperModel] = None
    _model_lock = threading.Lock()
    _loaded_model_name: Optional[str] = None

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def _get_or_load_model(self) -> WhisperModel:
        """Thread-safe lazy initialization and reuse of the WhisperModel singleton."""
        if (
            FasterWhisperProvider._model_instance is not None
            and FasterWhisperProvider._loaded_model_name == self.settings.WHISPER_MODEL
        ):
            return FasterWhisperProvider._model_instance

        with FasterWhisperProvider._model_lock:
            # Double-check locking
            if (
                FasterWhisperProvider._model_instance is not None
                and FasterWhisperProvider._loaded_model_name == self.settings.WHISPER_MODEL
            ):
                return FasterWhisperProvider._model_instance

            model_size = self.settings.WHISPER_MODEL
            device = self.settings.WHISPER_DEVICE
            compute_type = self.settings.WHISPER_COMPUTE_TYPE

            logger.info(
                "loading_faster_whisper_model",
                model=model_size,
                device=device,
                compute_type=compute_type,
            )
            t0 = time.perf_counter()

            try:
                model = WhisperModel(
                    model_size_or_path=model_size,
                    device=device,
                    compute_type=compute_type,
                    download_root=None,  # Use standard HF / ctranslate2 cache
                )
                FasterWhisperProvider._model_instance = model
                FasterWhisperProvider._loaded_model_name = model_size
                load_ms = (time.perf_counter() - t0) * 1000
                logger.info(
                    "faster_whisper_model_loaded",
                    model=model_size,
                    duration_ms=round(load_ms, 2),
                )
                return model
            except Exception as e:
                logger.error("failed_to_load_whisper_model", error=str(e), model=model_size)
                raise ModelUnavailableError(
                    f"Failed to load local Faster-Whisper model '{model_size}': {str(e)}",
                    details={"model": model_size, "device": device},
                )

    def _transcribe_sync(
        self,
        file_path: Path,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Synchronous CPU transcription executed in thread pool."""
        model = self._get_or_load_model()
        t0 = time.perf_counter()

        lang_param = language or self.settings.WHISPER_LANGUAGE

        try:
            segments_gen, info = model.transcribe(
                audio=str(file_path),
                language=lang_param,
                beam_size=5,
                temperature=0.0,
                vad_filter=True,  # Voice activity detection to trim silence
            )

            # Consume segments generator
            segments_list: List[TranscriptionSegment] = []
            full_text_chunks: List[str] = []

            for seg in segments_gen:
                seg_text = seg.text.strip()
                if seg_text:
                    segments_list.append(
                        TranscriptionSegment(
                            start=float(seg.start),
                            end=float(seg.end),
                            text=seg_text,
                            avg_logprob=float(getattr(seg, "avg_logprob", 0.0)),
                            no_speech_prob=float(getattr(seg, "no_speech_prob", 0.0)),
                        )
                    )
                    full_text_chunks.append(seg_text)

            full_text = " ".join(full_text_chunks).strip()
            total_duration_ms = (time.perf_counter() - t0) * 1000

            logger.info(
                "transcription_completed",
                file=file_path.name,
                language=info.language,
                language_probability=round(info.language_probability, 4),
                duration_seconds=round(info.duration, 2),
                text_preview=(full_text[:80] + "...") if len(full_text) > 80 else full_text,
                duration_ms=round(total_duration_ms, 2),
            )

            return TranscriptionResult(
                text=full_text,
                language=info.language,
                language_probability=float(info.language_probability),
                duration_seconds=float(info.duration),
                segments=segments_list,
            )

        except Exception as e:
            logger.error("transcription_failed", file=file_path.name, error=str(e))
            raise TranscriptionError(
                f"Audio transcription failed: {str(e)}",
                details={"file": file_path.name},
            )

    async def transcribe_audio(
        self,
        file_path: Path,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Asynchronously transcribe an audio file offloading CPU work to thread pool.
        """
        return await asyncio.to_thread(self._transcribe_sync, file_path, language)

    async def check_health(self) -> bool:
        """Check if model can be initialized or is already loaded."""
        try:
            await asyncio.to_thread(self._get_or_load_model)
            return True
        except Exception:
            return False
