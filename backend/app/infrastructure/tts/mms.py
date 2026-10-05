"""
Meta MMS-TTS provider implementation for offline Kannada speech synthesis on CPU.
Uses facebook/mms-tts-kan VITS architecture via Hugging Face Transformers and PyTorch.
"""

import asyncio
import io
import time
import wave
from typing import List, Optional
import numpy as np
import structlog
import torch

from app.core.errors import AppException
from app.domain.ports.tts import AudioSynthesisResult, ITTSProvider

logger = structlog.get_logger(__name__)

DEFAULT_MMS_MODEL_ID = "facebook/mms-tts-kan"


class MMSTTSProvider(ITTSProvider):
    """
    Offline Text-to-Speech provider using Meta MMS-TTS (VITS) for Kannada synthesis.
    """

    SUPPORTED_LANGUAGES = ["kn", "kan", "kn_in"]

    def __init__(
        self,
        model_id: str = DEFAULT_MMS_MODEL_ID,
        local_files_only: bool = True,
    ):
        self.model_id = model_id
        self.local_files_only = local_files_only
        self._tokenizer = None
        self._model = None
        self._lock = asyncio.Lock()

    def _load_model_sync(self):
        """Synchronously load MMS VITS model and tokenizer on CPU."""
        if self._model is not None and self._tokenizer is not None:
            return self._tokenizer, self._model

        from transformers import AutoTokenizer, VitsModel

        t0 = time.perf_counter()
        try:
            # First try loading from local huggingface cache
            tokenizer = AutoTokenizer.from_pretrained(self.model_id, local_files_only=self.local_files_only)
            model = VitsModel.from_pretrained(self.model_id, local_files_only=self.local_files_only)
        except Exception as local_err:
            if self.local_files_only:
                logger.warning(
                    "Local MMS-TTS load failed, falling back to online fetch once...",
                    error=str(local_err),
                )
                tokenizer = AutoTokenizer.from_pretrained(self.model_id, local_files_only=False)
                model = VitsModel.from_pretrained(self.model_id, local_files_only=False)
            else:
                raise AppException(
                    status_code=503,
                    message=f"Failed to load MMS-TTS Kannada model: {str(local_err)}",
                )

        model.eval()
        self._tokenizer = tokenizer
        self._model = model

        load_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "Meta MMS-TTS Kannada model loaded successfully",
            model_id=self.model_id,
            load_ms=round(load_ms, 2),
            sampling_rate=model.config.sampling_rate,
        )
        return self._tokenizer, self._model

    def _synthesize_sync(self, text: str) -> AudioSynthesisResult:
        """Synthesize Kannada Unicode text to in-memory 16-bit PCM WAV bytes."""
        tokenizer, model = self._load_model_sync()
        if not text or not text.strip():
            raise AppException(status_code=400, message="Cannot synthesize empty text.")

        t0 = time.perf_counter()
        inputs = tokenizer(text, return_tensors="pt")
        with torch.no_grad():
            output = model(**inputs).waveform

        synth_ms = (time.perf_counter() - t0) * 1000

        # Convert float32 tensor waveform into 16-bit signed integer PCM
        waveform = output.squeeze().cpu().numpy()
        sample_rate = model.config.sampling_rate

        # Normalize and clip to [-1.0, 1.0] range
        waveform_norm = np.clip(waveform, -1.0, 1.0)
        waveform_int16 = (waveform_norm * 32767.0).astype(np.int16)
        raw_pcm_bytes = waveform_int16.tobytes()

        # Write standard 16-bit PCM Mono WAV directly into BytesIO
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(sample_rate)
            wf.writeframes(raw_pcm_bytes)

        raw_wav_bytes = buf.getvalue()
        duration_s = len(waveform_int16) / float(sample_rate) if sample_rate > 0 else 0.0
        rtf = (synth_ms / 1000.0) / duration_s if duration_s > 0 else 0.0

        logger.debug(
            "Synthesized Kannada speech",
            text_len=len(text),
            duration_s=round(duration_s, 2),
            synth_ms=round(synth_ms, 2),
            rtf=round(rtf, 3),
        )

        return AudioSynthesisResult(
            audio_bytes=raw_wav_bytes,
            sample_rate=sample_rate,
            channels=1,
            sample_width=2,
            duration_seconds=duration_s,
            mime_type="audio/wav",
        )

    async def synthesize(
        self,
        text: str,
        language: str = "kn",
        speaker_id: Optional[str] = None,
    ) -> AudioSynthesisResult:
        """Synthesize Kannada speech audio asynchronously without blocking event loop."""
        return await asyncio.to_thread(self._synthesize_sync, text)

    async def check_health(self) -> bool:
        """Check if MMS-TTS model can be loaded locally."""
        try:
            await asyncio.to_thread(self._load_model_sync)
            return True
        except Exception as e:
            logger.warning("MMSTTSProvider health check failed", error=str(e))
            return False

    def get_supported_languages(self) -> List[str]:
        return ["kn"]
