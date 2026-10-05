"""
Text normalization, Unicode cleaning, and diacritic mapping for search keys.
Ensures accurate retrieval matches across English, Kannada, and IAST diacritic variations
while strictly preserving original source text for citations.
"""

import re
import unicodedata
from typing import List


# Custom phonetic/IAST character mapping replacements for Indian heritage terms
_IAST_CHAR_MAP = {
    "ś": "sh",
    "Ś": "Sh",
    "ṣ": "sh",
    "Ṣ": "Sh",
    "ḷ": "l",
    "Ḷ": "L",
    "ṛ": "ri",
    "Ṛ": "Ri",
    "ṇ": "n",
    "Ṇ": "N",
    "ñ": "n",
    "Ñ": "N",
    "ṅ": "n",
    "Ṅ": "N",
    "ṭ": "t",
    "Ṭ": "T",
    "ḍ": "d",
    "Ḍ": "D",
    "ṃ": "m",
    "Ṃ": "M",
    "ḥ": "h",
    "Ḥ": "H",
}


def normalize_query_for_search(text: str) -> str:
    """
    Normalize user search queries for consistent lexical and semantic matching.
    Applies Unicode NFC normalization, maps IAST diacritics, and strips extra whitespace.
    """
    if not text:
        return ""
    
    # 1. Base NFC normalization
    normalized = unicodedata.normalize("NFC", text.strip())
    
    # 2. Map specialized IAST consonants first
    for src, dst in _IAST_CHAR_MAP.items():
        if src in normalized:
            normalized = normalized.replace(src, dst)
            
    # 3. Strip Latin combining diacritical marks (e.g. ē -> e, ā -> a, ū -> u, ī -> i)
    decomposed = unicodedata.normalize("NFKD", normalized)
    cleaned_chars = []
    for c in decomposed:
        code = ord(c)
        # Drop Latin combining diacritics (0x0300-0x036F) and pre-Indic combining marks
        if unicodedata.combining(c) and code < 0x0900:
            continue
        cleaned_chars.append(c)
    cleaned = "".join(cleaned_chars)

    # Re-normalize to NFC and clean whitespace
    res = unicodedata.normalize("NFC", cleaned)
    return re.sub(r"\s+", " ", res).strip()


def tokenize_for_bm25(text: str) -> List[str]:
    """
    Tokenize text into lowercase lexical tokens for BM25 indexing and querying.
    Preserves Kannada words (\u0C80-\u0CFF), English words, and numeric tokens.
    """
    if not text:
        return []
    
    # Normalize diacritics for uniform token matching
    normalized = normalize_query_for_search(text).lower()
    
    # Extract alphanumeric words and Kannada Unicode blocks
    # \w in Python 3 includes Unicode word characters (Kannada script characters)
    tokens = re.findall(r"[\w\u0C80-\u0CFF]+", normalized)
    
    # Filter single-character punctuation/debris but preserve numbers and meaningful tokens
    return [t for t in tokens if len(t) > 0]
