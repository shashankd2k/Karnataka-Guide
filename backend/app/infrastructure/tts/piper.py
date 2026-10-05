"""
Piper TTS provider implementation for offline English speech synthesis on CPU.
Uses piper-tts with local ONNX models.
"""

import asyncio
import io
import time
import urllib.request
import wave
from pathlib import Path
from typing import List, Optional
import structlog

from app.core.errors import AppException
from app.domain.ports.tts import AudioSynthesisResult, ITTSProvider

logger = structlog.get_logger(__name__)

# Default paths for English voice model
DEFAULT_VOICE_NAME = "en_US-lessac-medium"
DEFAULT_MODEL_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
DEFAULT_CONFIG_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"


class PiperTTSProvider(ITTSProvider):
    """
    Offline Text-to-Speech provider using Piper TTS ONNX engine for English synthesis.
    """

    SUPPORTED_LANGUAGES = ["en", "en_us", "en_gb", "en_in", "en_au"]

    def __init__(
        self,
        model_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        auto_download: bool = False,
    ):
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.voices_dir = base_dir / "storage" / "models" / "voices" / "en"
        self.model_path = model_path or (self.voices_dir / f"{DEFAULT_VOICE_NAME}.onnx")
        self.config_path = config_path or (self.voices_dir / f"{DEFAULT_VOICE_NAME}.onnx.json")
        self.auto_download = auto_download
        self._voice = None
        self._lock = asyncio.Lock()

    def _ensure_model_files(self) -> None:
        """Verify local voice model files exist, downloading only if auto_download is enabled."""
        if not self.model_path.exists() or not self.config_path.exists():
            if self.auto_download:
                self.voices_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Downloading Piper English voice files...", model_path=str(self.model_path))
                if not self.model_path.exists():
                    urllib.request.urlretrieve(DEFAULT_MODEL_URL, self.model_path)
                if not self.config_path.exists():
                    urllib.request.urlretrieve(DEFAULT_CONFIG_URL, self.config_path)
                logger.info("Piper English voice files downloaded successfully.")
            else:
                raise AppException(
                    status_code=503,
                    message=f"Piper English voice model not found at {self.model_path}. Please download voice files.",
                )

    def _load_voice_sync(self):
        """Synchronously load PiperVoice model on CPU."""
        if self._voice is not None:
            return self._voice

        self._ensure_model_files()
        try:
            from piper.voice import PiperVoice

            t0 = time.perf_counter()
            self._voice = PiperVoice.load(
                model_path=str(self.model_path),
                config_path=str(self.config_path),
                use_cuda=False,
            )
            load_ms = (time.perf_counter() - t0) * 1000
            logger.info(
                "Piper English voice model loaded successfully",
                voice=DEFAULT_VOICE_NAME,
                load_ms=round(load_ms, 2),
            )
            return self._voice
        except Exception as e:
            logger.error("Failed to load Piper English voice", error=str(e))
            raise AppException(status_code=500, message=f"Failed to initialize Piper TTS: {str(e)}")

    def _synthesize_sync(self, text: str) -> AudioSynthesisResult:
        """Synthesize English text to in-memory 16-bit PCM WAV bytes."""
        voice = self._load_voice_sync()
        if not text or not text.strip():
            raise AppException(status_code=400, message="Cannot synthesize empty text.")

        t0 = time.perf_counter()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)

        synth_ms = (time.perf_counter() - t0) * 1000
        raw_bytes = buf.getvalue()

        # Read back WAV headers from buffer to verify and extract exact audio metadata
        buf.seek(0)
        with wave.open(buf, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            duration_s = n_frames / float(framerate) if framerate > 0 else 0.0

        rtf = (synth_ms / 1000.0) / duration_s if duration_s > 0 else 0.0
        logger.debug(
            "Synthesized English speech",
            text_len=len(text),
            duration_s=round(duration_s, 2),
            synth_ms=round(synth_ms, 2),
            rtf=round(rtf, 3),
        )

        return AudioSynthesisResult(
            audio_bytes=raw_bytes,
            sample_rate=framerate,
            channels=n_channels,
            sample_width=sampwidth,
            duration_seconds=duration_s,
            mime_type="audio/wav",
        )

    async def synthesize(
        self,
        text: str,
        language: str = "en",
        speaker_id: Optional[str] = None,
    ) -> AudioSynthesisResult:
        """Synthesize English speech audio asynchronously without blocking event loop."""
        return await asyncio.to_thread(self._synthesize_sync, text)

    async def check_health(self) -> bool:
        """Check if local voice files exist and model can be loaded."""
        try:
            await asyncio.to_thread(self._load_voice_sync)
            return True
        except Exception as e:
            logger.warning("PiperTTSProvider health check failed", error=str(e))
            return False

    def get_supported_languages(self) -> List[str]:
        return ["en"]
