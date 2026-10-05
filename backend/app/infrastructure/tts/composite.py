"""
Composite TTS Provider routing speech synthesis requests across Piper (English) and Meta MMS-TTS (Kannada).
"""

from typing import List, Optional
import structlog

from app.core.errors import AppException
from app.domain.ports.tts import AudioSynthesisResult, ITTSProvider
from app.infrastructure.tts.mms import MMSTTSProvider
from app.infrastructure.tts.piper import PiperTTSProvider

logger = structlog.get_logger(__name__)


class CompositeTTSProvider(ITTSProvider):
    """
    Unified multi-engine TTS provider that routes requests based on language.
    - English ('en') -> PiperTTSProvider (ONNX Lessac Medium, 22,050 Hz)
    - Kannada ('kn') -> MMSTTSProvider (VITS facebook/mms-tts-kan, 16,000 Hz)
    """

    ENGLISH_ALIASES = {"en", "en_us", "en_gb", "en_in", "en_au", "eng"}
    KANNADA_ALIASES = {"kn", "kan", "kn_in", "kannada"}

    def __init__(
        self,
        piper_provider: Optional[PiperTTSProvider] = None,
        mms_provider: Optional[MMSTTSProvider] = None,
    ):
        self._piper = piper_provider or PiperTTSProvider()
        self._mms = mms_provider or MMSTTSProvider()

    def _resolve_target_provider(self, language: str) -> tuple[ITTSProvider, str]:
        """Resolve the appropriate provider and canonical language code."""
        if not language:
            return self._piper, "en"

        norm_lang = language.strip().lower()
        if norm_lang in self.ENGLISH_ALIASES:
            return self._piper, "en"
        elif norm_lang in self.KANNADA_ALIASES:
            return self._mms, "kn"
        else:
            raise AppException(
                status_code=400,
                message=f"Unsupported TTS language: '{language}'. Supported languages are 'en' (English) and 'kn' (Kannada).",
            )

    async def synthesize(
        self,
        text: str,
        language: str = "en",
        speaker_id: Optional[str] = None,
    ) -> AudioSynthesisResult:
        """
        Synthesize speech using the appropriate language engine.
        """
        provider, canon_lang = self._resolve_target_provider(language)
        return await provider.synthesize(text=text, language=canon_lang, speaker_id=speaker_id)

    async def check_health(self) -> bool:
        """Verify health of both underlying TTS engines."""
        piper_ok = await self._piper.check_health()
        mms_ok = await self._mms.check_health()
        return piper_ok and mms_ok

    def get_supported_languages(self) -> List[str]:
        return ["en", "kn"]
