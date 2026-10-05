"""
Application Service for Multilingual Translation Orchestration.
Coordinates direction-aware proper-noun, historical date, and citation marker protection with deterministic verification.
"""

import re
from typing import Dict, List, Optional, Pattern, Tuple
import structlog

from app.core.config import get_settings
from app.domain.ports.translation import ITranslationProvider
from app.infrastructure.translation.nllb import NLLBTranslationProvider

logger = structlog.get_logger(__name__)


# Canonical Kannada -> English Heritage Proper Noun Mapping
KANNADA_TO_ENGLISH_HERITAGE: Dict[str, str] = {
    "ಚೆನ್ನಕೇಶವ": "Chennakeshava",
    "ಹೊಯ್ಸಳೇಶ್ವರ": "Hoysaleswara",
    "ವಿಷ್ಣುವರ್ಧನ": "Vishnuvardhana",
    "ವಿರೂಪಾಕ್ಷ": "Virupaksha",
    "ವಿಜಯನಗರ": "Vijayanagara",
    "ಪಟ್ಟದಕಲ್ಲು": "Pattadakal",
    "ಪಟ್ಟದಕಲ್": "Pattadakal",
    "ಹಳೇಬೀಡು": "Halebidu",
    "ಹಳೆಬೀಡು": "Halebidu",
    "ಐಹೊಳೆ": "Aihole",
    "ಐಹೋಳೆ": "Aihole",
    "ಬಾದಾಮಿ": "Badami",
    "ವಿಠ್ಠಲ": "Vittala",
    "ವಿಠಲ": "Vittala",
    "ಬೇಲೂರು": "Belur",
    "ಹಂಪಿ": "Hampi",
    "ದರ್ಪಣ ಸುಂದರಿ": "Darpana Sundari",
    "ಕಾಗಿನೆಲೆ": "Kaginele",
    "ಶ್ರವಣಬೆಳಗೊಳ": "Shravanabelagola",
    "ಗೊಮ್ಮಟೇಶ್ವರ": "Gommateshwara",
}

# English Heritage Proper Nouns requiring protection
CANONICAL_ENGLISH_HERITAGE_ENTITIES: List[str] = [
    "Chennakeshava",
    "Hoysaleswara",
    "Vishnuvardhana",
    "Virupaksha",
    "Vijayanagara",
    "Pattadakal",
    "Halebidu",
    "Aihole",
    "Badami",
    "Vittala",
    "Belur",
    "Hampi",
    "Darpana Sundari",
    "Kaginele",
    "Shravanabelagola",
    "Gommateshwara",
]

# Combined list for general protection
HERITAGE_PROPER_NOUNS: List[str] = (
    CANONICAL_ENGLISH_HERITAGE_ENTITIES + list(KANNADA_TO_ENGLISH_HERITAGE.keys())
)

# Historical dates, eras, and epochs
HISTORICAL_DATE_PATTERNS: List[str] = [
    r"\b\d{3,4}\s*(?:CE|BCE|AD|BC)\b",
    r"\b\d{1,2}(?:st|nd|rd|th)\s+century\b",
]

# Citation markers embedded in textual answers
CITATION_PATTERN: Pattern = re.compile(r"\[\d+\]")


class TranslationService:
    """
    Coordinates entity-preserving translation between Kannada and English.
    Implements direction-aware restoration, strict placeholder integrity, and fail-safe unmasking.
    """

    def __init__(self, provider: Optional[ITranslationProvider] = None):
        self.provider = provider or NLLBTranslationProvider()
        self.settings = get_settings()

    @staticmethod
    def prepare_retrieval_query(query: str) -> Tuple[str, List[str]]:
        """
        Substitute protected Kannada heritage entities with their canonical English forms
        prior to Kannada -> English retrieval translation.

        Returns:
            Tuple of (prepared_query_string, list_of_detected_canonical_entities)
        """
        if not query:
            return query, []

        prepared = query
        detected_entities: List[str] = []

        # Sort Kannada keys by length descending to match compound terms first
        sorted_kn_terms = sorted(KANNADA_TO_ENGLISH_HERITAGE.keys(), key=len, reverse=True)
        for kn_term in sorted_kn_terms:
            canonical_en = KANNADA_TO_ENGLISH_HERITAGE[kn_term]
            if kn_term in prepared:
                if canonical_en not in detected_entities:
                    detected_entities.append(canonical_en)
                prepared = prepared.replace(kn_term, canonical_en)

        # Also detect if canonical English entities were already present in the query
        for en_term in CANONICAL_ENGLISH_HERITAGE_ENTITIES:
            pat = re.compile(r"\b" + re.escape(en_term) + r"\b", re.IGNORECASE)
            if pat.search(query):
                if en_term not in detected_entities:
                    detected_entities.append(en_term)

        return prepared, detected_entities

    @staticmethod
    def mask_protected_tokens(text: str) -> Tuple[str, Dict[str, str]]:
        """
        Mask citation markers [1], heritage entities, and historical dates with placeholder tokens.
        Example:
            "The Chennakeshava Temple at Belur was built in 1117 CE [1]."
            -> ("The __HERITAGE_0__ Temple at __HERITAGE_1__ was built in __DATE_0__ __CIT_0__.", token_map)
        """
        if not text:
            return text, {}

        token_map: Dict[str, str] = {}
        masked_text = text
        counter = 0

        # 1. Mask Citation Labels: [1], [2], [3]
        def cite_repl(match):
            nonlocal counter
            tag = f"__CIT_{counter}__"
            token_map[tag] = match.group(0)
            counter += 1
            return tag

        masked_text = CITATION_PATTERN.sub(cite_repl, masked_text)

        # 2. Mask Historical Dates / Epochs
        date_counter = 0
        for pat in HISTORICAL_DATE_PATTERNS:
            def date_repl(match):
                nonlocal date_counter
                tag = f"__DATE_{date_counter}__"
                token_map[tag] = match.group(0)
                date_counter += 1
                return tag

            masked_text = re.sub(pat, date_repl, masked_text, flags=re.IGNORECASE)

        # 3. Mask Heritage Proper Nouns (sorted by length descending)
        noun_counter = 0
        sorted_nouns = sorted(HERITAGE_PROPER_NOUNS, key=len, reverse=True)
        for noun in sorted_nouns:
            if any(ord(c) > 127 for c in noun):
                noun_pattern = re.compile(re.escape(noun))
            else:
                noun_pattern = re.compile(r"\b" + re.escape(noun) + r"\b", flags=re.IGNORECASE)

            if noun_pattern.search(masked_text):
                tag = f"__HERITAGE_{noun_counter}__"
                matched_match = noun_pattern.search(masked_text)
                if matched_match:
                    token_map[tag] = matched_match.group(0)
                    masked_text = noun_pattern.sub(tag, masked_text)
                    noun_counter += 1

        return masked_text, token_map

    @staticmethod
    def verify_placeholder_integrity(text: str, token_map: Dict[str, str]) -> bool:
        """
        Check if all placeholders in token_map are intact in the translated text.
        """
        if not token_map:
            return True
        for placeholder in token_map.keys():
            if placeholder in text:
                continue
            fuzzy_pat = re.compile(
                re.escape(placeholder).replace(r"\_", r"[\s\_]?"),
                re.IGNORECASE,
            )
            if not fuzzy_pat.search(text):
                return False
        return True

    @staticmethod
    def unmask_protected_tokens(
        text: str,
        token_map: Dict[str, str],
        strict_citations: bool = False,
    ) -> str:
        """
        Restore original protected tokens from placeholder map with fail-safe validation.

        Args:
            text: Translated string with placeholders.
            token_map: Mapping from placeholder tag to original token.
            strict_citations: If True, detects missing citation placeholders without false appendage.

        Returns:
            Restored text string.
        """
        if not text or not token_map:
            return text

        restored = text

        for placeholder, original in token_map.items():
            # 1. Exact replacement
            if placeholder in restored:
                restored = restored.replace(placeholder, original)
            else:
                # 2. Fuzzy fallback for minor whitespace/case alterations
                fuzzy_pat = re.compile(
                    re.escape(placeholder).replace(r"\_", r"[\s\_]?"),
                    re.IGNORECASE,
                )
                if fuzzy_pat.search(restored):
                    restored = fuzzy_pat.sub(original, restored)
                else:
                    logger.warning(
                        "translation_placeholder_missing",
                        placeholder=placeholder,
                        original=original,
                    )
                    # Do NOT append citations to arbitrary locations if strict_citations is requested
                    if not strict_citations and placeholder.startswith("__CIT_"):
                        restored = f"{restored} {original}"

        return restored

    async def translate_retrieval_query(
        self,
        query: str,
        from_lang: str,
        to_lang: str = "en",
    ) -> str:
        """
        Translate a tourist search query from Kannada to English for Phase 7 retrieval.
        Guarantees that all protected heritage proper nouns are preserved in their canonical English forms.
        If query is already in English, returns it unchanged (zero overhead).
        """
        normalized_from = from_lang.strip().lower()
        normalized_to = to_lang.strip().lower()

        # Rule: English query bypasses unnecessary translation
        if normalized_from == "en" or normalized_from == normalized_to:
            return query

        clean_query = query.strip()
        if not clean_query:
            return query

        try:
            # 1. Direction-aware canonical entity substitution
            prepared_query, detected_entities = self.prepare_retrieval_query(clean_query)

            # 2. Offline neural translation
            translated = await self.provider.translate(
                text=prepared_query,
                from_lang=normalized_from,
                to_lang=normalized_to,
            )

            # 3. Post-translation placeholder and entity integrity verification
            final_query = translated.strip()
            for entity in detected_entities:
                entity_pat = re.compile(r"\b" + re.escape(entity) + r"\b", re.IGNORECASE)
                if not entity_pat.search(final_query):
                    # Deterministic restoration: if model dropped the entity, insert it safely
                    logger.warning(
                        "retrieval_entity_restored_post_translation",
                        missing_entity=entity,
                        translated_query=final_query,
                    )
                    if re.search(r"\btemple\b", final_query, re.IGNORECASE):
                        final_query = re.sub(
                            r"\b(temple)\b",
                            f"{entity} \\1",
                            final_query,
                            flags=re.IGNORECASE,
                            count=1,
                        )
                    else:
                        final_query = f"{entity} {final_query}"

            logger.info(
                "retrieval_query_translated",
                original_query=clean_query,
                prepared_query=prepared_query,
                translated_query=final_query,
                detected_entities=detected_entities,
                from_lang=from_lang,
                to_lang=to_lang,
            )
            return final_query
        except Exception as e:
            logger.warning(
                "retrieval_query_translation_failed_using_original",
                error=str(e),
                query=query,
            )
            # Fail safe: return original query
            return query

    async def translate_response(
        self,
        response: str,
        from_lang: str = "en",
        to_lang: str = "kn",
    ) -> str:
        """
        Translate a grounded assistant response from English to Kannada.
        Preserves embedded citation labels ([1], [2]) and heritage entities verbatim.
        If citation placeholders cannot be preserved with 100% integrity, falls back safely to
        original grounded English text to avoid false factual misattributions.
        """
        normalized_from = from_lang.strip().lower()
        normalized_to = to_lang.strip().lower()

        if normalized_to == "en" or normalized_from == normalized_to:
            return response

        clean_response = response.strip()
        if not clean_response:
            return response

        # Deterministic instant return for standard fallback strings (zero translation overhead)
        if clean_response in (
            "Information is not available in the knowledge base.",
            "Information is not available in the knowledge base",
        ):
            return "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."

        try:
            # 1. Mask citations and entities
            masked_text, token_map = self.mask_protected_tokens(clean_response)

            # 2. Check placeholder integrity expectation
            # 3. Translate masked text
            translated_masked = await self.provider.translate(
                text=masked_text,
                from_lang=normalized_from,
                to_lang=normalized_to,
            )

            # 4. Verify placeholder integrity
            is_valid = self.verify_placeholder_integrity(translated_masked, token_map)

            # 5. If citation markers were corrupted, do not fabricate citations on arbitrary sentences
            if not is_valid and any(k.startswith("__CIT_") for k in token_map):
                logger.warning(
                    "response_translation_citation_corrupted_falling_back_to_english",
                    chars_in=len(clean_response),
                )
                return clean_response

            # 6. Unmask
            final_kannada_response = self.unmask_protected_tokens(
                translated_masked,
                token_map,
                strict_citations=True,
            )

            logger.info(
                "grounded_response_translated",
                chars_in=len(clean_response),
                chars_out=len(final_kannada_response),
                citation_tags_count=len([k for k in token_map if k.startswith("__CIT_")]),
            )
            return final_kannada_response
        except Exception as e:
            logger.error(
                "response_translation_failed",
                error=str(e),
            )
            # Return original English response if translation fails rather than an ungrounded hallucination
            return response
