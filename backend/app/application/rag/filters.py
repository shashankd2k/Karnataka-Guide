"""
Heuristic noise filtering, bibliography/reference suppression, and near-duplicate removal.
"""

import re
from typing import List, Set
from app.application.rag.schemas import RetrievalCandidate

# Regular expressions identifying bibliography, citation lists, and table of contents
_BIBLIOGRAPHY_SECTION_PATTERNS = [
    r"^references?$",
    r"^bibliography$",
    r"^works cited$",
    r"^further reading$",
    r"^selected bibliography$",
    r"^table of contents$",
    r"^contents$",
    r"^index$",
]

_BIBLIOGRAPHY_TEXT_INDICATORS = [
    r"\[\d+\]\s+[A-Z]",  # [1] Author Name
    r"pp\.\s*\d+[-–]\d+",  # pp. 120-145
    r"ISBN(?:-1[03])?:?\s*[\d-]+",
    r"vol\.\s*\d+,\s*no\.\s*\d+",
    r"journal of\s+[a-z]+",
    r"archaeological survey of india",
    r"press,\s*(?:19|20)\d{2}",
]


def is_bibliography_or_noise(candidate: RetrievalCandidate) -> bool:
    """
    Detect if a candidate chunk is primarily a bibliography, reference list, or table of contents.
    """
    section = (candidate.section or "").strip().lower()
    text = candidate.text.strip()
    
    # 1. Section Header match
    for pat in _BIBLIOGRAPHY_SECTION_PATTERNS:
        if re.search(pat, section):
            return True

    # 2. Strong text indicator density
    text_lower = text.lower()
    matches = sum(1 for pat in _BIBLIOGRAPHY_TEXT_INDICATORS if re.search(pat, text_lower))
    if matches >= 2:
        return True

    # 3. Table of contents dot leader lines (e.g. "Chapter 1 ............ 15")
    if text.count("....") >= 3:
        return True

    return False


def filter_noise_chunks(
    candidates: List[RetrievalCandidate],
    query_text: str,
) -> List[RetrievalCandidate]:
    """
    Remove or down-rank bibliography and structural noise chunks unless query explicitly requests references.
    """
    query_lower = query_text.lower()
    explicit_ref_query = any(k in query_lower for k in ["reference", "bibliography", "citation", "source book", "author"])

    if explicit_ref_query:
        return candidates

    clean_candidates: List[RetrievalCandidate] = []
    for candidate in candidates:
        if not is_bibliography_or_noise(candidate):
            clean_candidates.append(candidate)

    return clean_candidates


def suppress_duplicate_chunks(
    candidates: List[RetrievalCandidate],
    max_token_overlap: float = 0.80,
) -> List[RetrievalCandidate]:
    """
    Deduplicate identical chunks and suppress consecutive overlapping chunks from the same document page.
    """
    seen_chunk_ids: Set[str] = set()
    accepted: List[RetrievalCandidate] = []

    for candidate in candidates:
        if candidate.chunk_id in seen_chunk_ids:
            continue

        # Check lexical overlap with already accepted chunks from the same document & page
        candidate_words = set(candidate.text.lower().split())
        if not candidate_words:
            continue

        is_near_duplicate = False
        for prev in accepted:
            if prev.document_id == candidate.document_id and prev.page_number == candidate.page_number:
                prev_words = set(prev.text.lower().split())
                intersection = len(candidate_words & prev_words)
                union = len(candidate_words | prev_words)
                jaccard = intersection / union if union > 0 else 0.0

                if jaccard >= max_token_overlap:
                    is_near_duplicate = True
                    break

        if not is_near_duplicate:
            seen_chunk_ids.add(candidate.chunk_id)
            accepted.append(candidate)

    # Re-assign final_rank
    for idx, candidate in enumerate(accepted, start=1):
        candidate.final_rank = idx

    return accepted
