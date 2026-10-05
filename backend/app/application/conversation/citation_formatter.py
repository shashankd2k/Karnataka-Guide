"""
Citation formatter and extractive evidence compiler for Phase 8.

Compiles verified, verbatim source passages with authentic page-level
citation tokens without synthetic or hallucinated LLM filler text.
"""

from typing import List, Tuple, Dict, Any, Optional
from app.application.rag.schemas import RetrievalCandidate
from app.application.conversation.grounding_guard import GroundingResult


def extract_authoritative_citations(
    candidates: List[RetrievalCandidate],
    active_generation_id: Optional[str] = None,
    max_passages: int = 3,
) -> List[Dict[str, Any]]:
    """
    Extract authoritative citation metadata dictionaries directly from top retrieval candidates.
    Never relies on model-generated metadata.
    """
    citations: List[Dict[str, Any]] = []
    for idx, cand in enumerate(candidates[:max_passages], 1):
        citations.append({
            "citation_label": f"[{idx}]",
            "chunk_id": cand.chunk_id,
            "document_id": cand.document_id,
            "source_filename": cand.source_filename,
            "page_number": cand.page_number,
            "section_header": cand.section,
            "generation_id": active_generation_id,
            "reranker_score": cand.reranker_score,
        })
    return citations


def sanitize_model_citations(answer: str, authorized_labels: List[str]) -> str:
    """
    Validate and sanitize inline citation tokens emitted by the LLM.
    Removes unknown/unauthorized citation numbers, trims simulated dialogue continuation,
    and ensures clean citation placement.
    """
    import re
    if not answer:
        return answer

    # Defensive boundary trimming: stop at simulated continuation / dialogue leaks
    boundary_patterns = [
        r"\n+Tourist Question:.*",
        r"\n+Tourist:.*",
        r"\n+Question:.*",
        r"\n+User:.*",
        r"\n+Assistant:.*",
        r"\n*###.*",
    ]
    for pattern in boundary_patterns:
        answer = re.split(pattern, answer, flags=re.IGNORECASE)[0].strip()

    if not authorized_labels:
        return answer

    auth_set = set(authorized_labels)

    def _replace_label(match: re.Match) -> str:
        label = match.group(0)
        return label if label in auth_set else ""

    # Replace any unauthorized brackets like [4] or [99]
    sanitized = re.sub(r"\[\d+\]", _replace_label, answer)
    # Clean up double spaces created by removal
    sanitized = re.sub(r"[ \t]{2,}", " ", sanitized).strip()

    # If the model didn't include any citation token at all, attach the primary citation [1]
    has_any_auth = any(label in sanitized for label in authorized_labels)
    if not has_any_auth and authorized_labels:
        sanitized = f"{sanitized} {authorized_labels[0]}"

    return sanitized


def format_citations_and_evidence(
    candidates: List[RetrievalCandidate],
    grounding_result: GroundingResult,
    active_generation_id: Optional[str] = None,
    max_passages: int = 2,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format citation metadata and compile extractive source evidence text.

    Args:
        candidates: Top ranked RetrievalCandidate objects from Phase 7 retrieval.
        grounding_result: Result from GroundingGuard evaluation.
        active_generation_id: Current active knowledge generation UUID.
        max_passages: Maximum number of source passages to include in answer text.

    Returns:
        Tuple of (answer_text, list_of_citation_dictionaries).
    """
    if not grounding_result.is_grounded or not candidates:
        fallback = grounding_result.fallback_message or "Information is not available in the knowledge base."
        return fallback, []

    citations = extract_authoritative_citations(
        candidates=candidates,
        active_generation_id=active_generation_id,
        max_passages=max_passages,
    )

    text_blocks: List[str] = []
    for idx, cand in enumerate(candidates[:max_passages], 1):
        label = f"[{idx}]"
        clean_text = cand.text.strip()
        text_blocks.append(f"{clean_text} {label}")

    compiled_answer = "\n\n".join(text_blocks)
    return compiled_answer, citations


def to_public_citation(citation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format citation dictionary for public tourist consumption.
    Strictly emits only: citation_label, source_filename, page_number, section_header.
    Guarantees zero internal fields (chunk_id, document_id, generation_id, reranker_score, raw text).
    """
    return {
        "citation_label": citation.get("citation_label", ""),
        "source_filename": citation.get("source_filename", ""),
        "page_number": citation.get("page_number", 1),
        "section_header": citation.get("section_header"),
    }


def filter_authoritative_citations(
    answer_text: str,
    authoritative_citations: List[Dict[str, Any]],
    public_only: bool = True,
) -> List[Dict[str, Any]]:
    """
    Filter server-authoritative citations so only citations actually referenced
    by label in the final visible answer are emitted, preserving order of first appearance.

    Guarantees:
    - Zero citations for fallbacks / unreferenced text
    - No duplicated citation labels
    - Citations ordered by first appearance in answer_text
    - If public_only=True, strips internal database/vector IDs and raw scores
    """
    import re

    if not answer_text or not authoritative_citations:
        return []

    # Find all citation labels in order of appearance in answer_text, e.g. ['[1]', '[2]']
    found_labels = re.findall(r"\[\d+\]", answer_text)
    if not found_labels:
        return []

    # Map label -> authoritative citation dict
    auth_map = {c["citation_label"]: c for c in authoritative_citations if "citation_label" in c}

    seen_labels = set()
    filtered: List[Dict[str, Any]] = []
    for label in found_labels:
        if label in auth_map and label not in seen_labels:
            seen_labels.add(label)
            cit = auth_map[label]
            filtered.append(to_public_citation(cit) if public_only else cit)

    return filtered

