"""
Abstract Domain Port for Multilingual Translation Providers.
Enforces clean architectural decoupling between business logic and concrete translation engines.
"""

from abc import ABC, abstractmethod
from typing import List


class ITranslationProvider(ABC):
    """
    Domain port interface for offline/online neural machine translation providers.
    """

    @abstractmethod
    async def translate(
        self,
        text: str,
        from_lang: str,
        to_lang: str,
    ) -> str:
        """
        Translate input text from source language to target language.

        Args:
            text: The text to translate.
            from_lang: Source language code (e.g., 'kn', 'en').
            to_lang: Target language code (e.g., 'en', 'kn').

        Returns:
            Translated text string.

        Raises:
            TranslationError: If translation fails or language is unsupported.
        """
        raise NotImplementedError

    @abstractmethod
    async def check_health(self) -> bool:
        """
        Verify that the translation provider, models, and dependencies are healthy.

        Returns:
            True if healthy and operational, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """
        List of supported language codes.

        Returns:
            List of supported language codes (e.g., ['en', 'kn']).
        """
        raise NotImplementedError
