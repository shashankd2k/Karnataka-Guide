"""
Infrastructure implementation of ITranslationProvider using Meta NLLB-200 Distilled 600M.
Provides 100% offline neural machine translation between Kannada (kan_Knda) and English (eng_Latn).
"""

import asyncio
import threading
import time
from typing import Dict, List, Optional, Tuple
import structlog
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from app.core.config import get_settings
from app.core.errors import AppException
from app.domain.ports.translation import ITranslationProvider

logger = structlog.get_logger(__name__)


# Language code mappings between ISO-639 codes and NLLB BCP-47 identifiers
NLLB_LANGUAGE_MAP: Dict[str, str] = {
    "kn": "kan_Knda",
    "kannada": "kan_Knda",
    "en": "eng_Latn",
    "english": "eng_Latn",
}

SUPPORTED_LANGUAGES: List[str] = ["en", "kn"]


class TranslationError(AppException):
    """Raised when translation execution fails."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            code="TRANSLATION_FAILED",
            status_code=500,
            details=details,
        )


class UnsupportedLanguageError(AppException):
    """Raised when an unsupported language code is provided."""

    def __init__(self, language: str):
        super().__init__(
            message=f"Language '{language}' is not supported for translation. Supported: {SUPPORTED_LANGUAGES}",
            code="UNSUPPORTED_TRANSLATION_LANGUAGE",
            status_code=400,
            details={"language": language, "supported": SUPPORTED_LANGUAGES},
        )


class NLLBTranslationProvider(ITranslationProvider):
    """
    Offline neural translation provider using Meta NLLB-200 Distilled 600M.
    Implements thread-safe lazy singleton model caching and non-blocking async execution.
    """

    _model_instance: Optional[AutoModelForSeq2SeqLM] = None
    _tokenizer_instance: Optional[AutoTokenizer] = None
    _lock = threading.Lock()

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ):
        settings = get_settings()
        self.model_name = model_name or settings.TRANSLATION_MODEL_NAME
        self.device = device or settings.TRANSLATION_DEVICE

    @classmethod
    def _get_model_and_tokenizer(
        cls,
        model_name: str,
        device: str,
    ) -> Tuple[AutoModelForSeq2SeqLM, AutoTokenizer]:
        """
        Thread-safe singleton loader for NLLB-200 model and tokenizer.
        """
        if cls._model_instance is None or cls._tokenizer_instance is None:
            with cls._lock:
                if cls._model_instance is None or cls._tokenizer_instance is None:
                    logger.info(
                        "loading_nllb_translation_model",
                        model=model_name,
                        device=device,
                    )
                    t0 = time.perf_counter()
                    try:
                        # Try loading from local huggingface cache first
                        try:
                            tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
                            model = AutoModelForSeq2SeqLM.from_pretrained(model_name, local_files_only=True)
                        except Exception:
                            tokenizer = AutoTokenizer.from_pretrained(model_name)
                            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
                        model.to(device)
                        model.eval()

                        cls._tokenizer_instance = tokenizer
                        cls._model_instance = model
                        
                        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
                        logger.info(
                            "nllb_translation_model_loaded",
                            model=model_name,
                            duration_ms=duration_ms,
                        )
                    except Exception as e:
                        logger.error(
                            "nllb_translation_model_load_failed",
                            model=model_name,
                            error=str(e),
                        )
                        raise TranslationError(
                            f"Failed to load NLLB-200 translation model '{model_name}': {e}"
                        ) from e

        return cls._model_instance, cls._tokenizer_instance

    def _normalize_lang_code(self, lang: str) -> str:
        """Map short language code to NLLB code (e.g. 'kn' -> 'kan_Knda')."""
        normalized = lang.strip().lower()
        if normalized not in NLLB_LANGUAGE_MAP:
            raise UnsupportedLanguageError(lang)
        return NLLB_LANGUAGE_MAP[normalized]

    def _sync_translate(
        self,
        text: str,
        from_nllb_lang: str,
        to_nllb_lang: str,
        max_new_tokens: int = 256,
    ) -> str:
        """
        Synchronous model inference on CPU.
        """
        model, tokenizer = self._get_model_and_tokenizer(self.model_name, self.device)

        tokenizer.src_lang = from_nllb_lang
        forced_bos_token_id = tokenizer.convert_tokens_to_ids(to_nllb_lang)

        inputs = tokenizer(text, return_tensors="pt")
        if self.device != "cpu":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            output_tokens = model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_new_tokens=max_new_tokens,
            )

        translated = tokenizer.decode(output_tokens[0], skip_special_tokens=True)
        return translated.strip()

    async def translate(
        self,
        text: str,
        from_lang: str,
        to_lang: str,
    ) -> str:
        """
        Translate text asynchronously in a background worker thread.
        """
        if not text or not text.strip():
            return text

        src_nllb = self._normalize_lang_code(from_lang)
        tgt_nllb = self._normalize_lang_code(to_lang)

        if src_nllb == tgt_nllb:
            return text

        t0 = time.perf_counter()
        try:
            translated = await asyncio.to_thread(
                self._sync_translate,
                text=text.strip(),
                from_nllb_lang=src_nllb,
                to_nllb_lang=tgt_nllb,
            )
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.debug(
                "translation_completed",
                from_lang=from_lang,
                to_lang=to_lang,
                duration_ms=duration_ms,
                chars_in=len(text),
                chars_out=len(translated),
            )
            return translated
        except AppException:
            raise
        except Exception as e:
            logger.error(
                "translation_execution_failed",
                from_lang=from_lang,
                to_lang=to_lang,
                error=str(e),
            )
            raise TranslationError(f"Translation execution failed: {e}") from e

    async def check_health(self) -> bool:
        """
        Check if model and tokenizer can be initialized successfully.
        """
        try:
            await asyncio.to_thread(
                self._get_model_and_tokenizer,
                self.model_name,
                self.device,
            )
            return True
        except Exception:
            return False

    def get_supported_languages(self) -> List[str]:
        """Return list of supported ISO language codes."""
        return list(SUPPORTED_LANGUAGES)
