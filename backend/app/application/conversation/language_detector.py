"""
Lightweight, deterministic Unicode-script language detector.

Supported in Phase 8:
- Pure English ('en'): Latin alphabet script.
- Pure Kannada ('kn'): Kannada Unicode block (U+0C80 to U+0CFF).
- Script-Mixed ('kn-mixed'): Kannada Unicode characters mixed with Latin script.

Documented Architectural Scope & Limitation:
- Romanized Kannada (e.g. 'Belur temple yaaru kattidru?') consists purely of ASCII/Latin
  characters and is classified as 'en' by script-based detection. Full Romanized transliteration
  and phonetic translation belong to Phase 11 (Offline Translation Hardening).
"""

from dataclasses import dataclass
import re
from typing import Literal

# Unicode range for Kannada script block: U+0C80 to U+0CFF
KANNADA_REGEX = re.compile(r"[\u0C80-\u0CFF]")
LATIN_REGEX = re.compile(r"[a-zA-Z]")


@dataclass(frozen=True)
class LanguageDetectionResult:
    """Language detection output."""
    language: Literal["en", "kn", "kn-mixed"]
    confidence: float
    kannada_char_count: int
    latin_char_count: int
    is_script_mixed: bool


def detect_language(text: str) -> LanguageDetectionResult:
    """
    Detect language based on Unicode character script distribution.

    Args:
        text: Raw user input text.

    Returns:
        LanguageDetectionResult with language code ('en', 'kn', or 'kn-mixed').
    """
    if not text or not text.strip():
        # Default platform language per PRD is Kannada ('kn')
        return LanguageDetectionResult(
            language="kn",
            confidence=0.5,
            kannada_char_count=0,
            latin_char_count=0,
            is_script_mixed=False,
        )

    kannada_matches = KANNADA_REGEX.findall(text)
    latin_matches = LATIN_REGEX.findall(text)

    k_count = len(kannada_matches)
    l_count = len(latin_matches)
    total_alpha = k_count + l_count

    if total_alpha == 0:
        return LanguageDetectionResult(
            language="kn",
            confidence=0.5,
            kannada_char_count=0,
            latin_char_count=0,
            is_script_mixed=False,
        )

    if k_count > 0 and l_count > 0:
        return LanguageDetectionResult(
            language="kn-mixed",
            confidence=0.95,
            kannada_char_count=k_count,
            latin_char_count=l_count,
            is_script_mixed=True,
        )

    if k_count > 0:
        return LanguageDetectionResult(
            language="kn",
            confidence=1.0,
            kannada_char_count=k_count,
            latin_char_count=0,
            is_script_mixed=False,
        )

    # Latin script only -> 'en'
    return LanguageDetectionResult(
        language="en",
        confidence=1.0,
        kannada_char_count=0,
        latin_char_count=l_count,
        is_script_mixed=False,
    )
