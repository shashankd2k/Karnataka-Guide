"""
Focused deterministic unit tests for prompt isolation, citation authorization,
evidence budgeting, boundary trimming, and exact fallback policies.
Runs completely offline without external DB or LLM dependencies.
"""

import pytest
from app.application.rag.schemas import RetrievalCandidate
from app.application.rag.prompt_builder import (
    EVIDENCE_START_TAG,
    EVIDENCE_END_TAG,
    ENGLISH_FALLBACK,
    KANNADA_FALLBACK,
    SYSTEM_POLICY_ENGLISH,
    SYSTEM_POLICY_KANNADA,
    select_grounded_candidates,
    compress_and_format_evidence,
    build_grounded_prompt,
)
from app.application.conversation.citation_formatter import (
    extract_authoritative_citations,
    sanitize_model_citations,
    filter_authoritative_citations,
    to_public_citation,
)


def _make_candidate(
    cid: str,
    text: str,
    doc: str = "Badami_Caves_Guide.pdf",
    page: int = 1,
    section: str = "Test Section",
    score: float = 1.0,
    rank: int = 1,
) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=cid,
        document_id="doc-uuid-1",
        generation_id="1a2c6365-1bee-4478-9599-a706ee5c7221",
        text=text,
        page_number=page,
        source_filename=doc,
        section=section,
        reranker_score=score,
        final_rank=rank,
    )


def test_character_budget_rejection_omits_unsupplied_label():
    """
    CONFIRMED DEFECT 1: When a candidate exceeds character budget,
    its label MUST NOT be appended to authorized_labels.
    """
    cand1 = _make_candidate("c1", "Passage one text with sufficient detail to occupy budget.", rank=1)
    # Cand 2 has a large body of text that will push total beyond max_chars
    cand2 = _make_candidate("c2", "Passage two " * 50, rank=2)

    # Set max_chars so cand1 fits (len ~120 chars with header), but cand1 + cand2 (~650 chars) exceeds 200
    evidence_block, auth_labels = compress_and_format_evidence([cand1, cand2], max_chars=200, max_passages=2)

    assert "[1]" in evidence_block
    assert "[2]" not in evidence_block
    assert auth_labels == ["[1]"], f"auth_labels must only contain [1], got {auth_labels}"
    assert "Passage one" in evidence_block
    assert "Passage two" not in evidence_block


def test_duplicate_passage_suppression_maintains_consecutive_labels():
    """
    CONFIRMED DEFECT 2: When candidate 2 is a near-duplicate of candidate 1,
    it is suppressed and candidate 3 receives consecutive label [2], matching auth_labels.
    """
    cand1 = _make_candidate("c1", "The Chennakeshava temple was commissioned in 1117 CE.", rank=1)
    # Near-duplicate of cand1
    cand2 = _make_candidate("c2", "The Chennakeshava temple was commissioned in 1117 CE.   ", rank=2)
    cand3 = _make_candidate("c3", "Madanika bracket figures depict dancers and musicians.", rank=3)

    accepted = select_grounded_candidates([cand1, cand2, cand3], max_chars=2000, max_passages=2)
    assert len(accepted) == 2
    assert accepted[0].chunk_id == "c1"
    assert accepted[1].chunk_id == "c3"

    evidence_block, auth_labels = compress_and_format_evidence([cand1, cand2, cand3], max_chars=2000, max_passages=2)
    assert auth_labels == ["[1]", "[2]"]
    assert "[1] (Source: Badami_Caves_Guide.pdf" in evidence_block
    assert "[2] (Source: Badami_Caves_Guide.pdf" in evidence_block
    assert "[3]" not in evidence_block


def test_sanitization_defensively_trims_simulated_dialogue():
    """
    CONFIRMED DEFECT 3 (Q18 continuation defect):
    Simulated dialogue leaks such as 'Tourist Question:', 'Tourist:', '###'
    must be cleanly truncated before returning to the tourist.
    """
    leaky_answer = (
        "The Lad Khan temple features sloped stone roof slabs and floral lattice windows. [1]\n\n"
        "Tourist Question: What is the architectural significance of the Lad Khan temple in Aihole?"
    )
    authorized = ["[1]"]

    sanitized = sanitize_model_citations(leaky_answer, authorized)
    assert "Tourist Question:" not in sanitized
    assert sanitized == "The Lad Khan temple features sloped stone roof slabs and floral lattice windows. [1]"

    # Test other simulated dialogue markers
    assert sanitize_model_citations("Fact answer. [1]\n\nTourist: Tell me more.", authorized) == "Fact answer. [1]"
    assert sanitize_model_citations("Fact answer. [1]\n\nQuestion: Next question?", authorized) == "Fact answer. [1]"
    assert sanitize_model_citations("Fact answer. [1]\n\n### Heading", authorized) == "Fact answer. [1]"


def test_citation_authorization_matches_evidence_supplied_to_model():
    """
    CONFIRMED DEFECT 4: Align citation extraction with accepted candidates
    so citation metadata exactly matches evidence provided to the prompt.
    """
    cand1 = _make_candidate("c1", "Evidence text 1", rank=1)
    cand2 = _make_candidate("c2", "Evidence text 2", rank=2)
    cand3 = _make_candidate("c3", "Evidence text 3 (should not be in citations if not in prompt)", rank=3)

    candidates = [cand1, cand2, cand3]
    accepted = select_grounded_candidates(candidates, max_chars=2000, max_passages=2)
    assert len(accepted) == 2

    cits = extract_authoritative_citations(accepted, active_generation_id="gen-test", max_passages=len(accepted))
    assert len(cits) == 2
    assert [c["citation_label"] for c in cits] == ["[1]", "[2]"]
    assert [c["chunk_id"] for c in cits] == ["c1", "c2"]


def test_filter_authoritative_citations_respects_answer_and_public_schema():
    """
    Verify filter_authoritative_citations emits only referenced citations,
    preserves first-appearance order, and strips internal fields.
    """
    authoritative = [
        {
            "citation_label": "[1]",
            "chunk_id": "uuid-1",
            "document_id": "doc-1",
            "source_filename": "Badami_Caves_Guide.pdf",
            "page_number": 3,
            "section_header": "Cave 4",
            "generation_id": "gen-1",
            "reranker_score": 2.5,
        },
        {
            "citation_label": "[2]",
            "chunk_id": "uuid-2",
            "document_id": "doc-2",
            "source_filename": "Pattadakal_UNESCO_Guide.pdf",
            "page_number": 1,
            "section_header": "Virupaksha",
            "generation_id": "gen-1",
            "reranker_score": 1.5,
        },
    ]

    # Only [2] referenced in answer
    answer = "The Virupaksha temple has intricate carvings. [2]"
    filtered = filter_authoritative_citations(answer, authoritative, public_only=True)
    assert len(filtered) == 1
    assert filtered[0]["citation_label"] == "[2]"
    assert filtered[0]["source_filename"] == "Pattadakal_UNESCO_Guide.pdf"
    assert "chunk_id" not in filtered[0]
    assert "reranker_score" not in filtered[0]

    # Both [2] then [1] referenced in answer -> order of appearance preserved
    answer_both = "Virupaksha [2] followed by Badami Cave 4 [1]."
    filtered_both = filter_authoritative_citations(answer_both, authoritative, public_only=True)
    assert len(filtered_both) == 2
    assert filtered_both[0]["citation_label"] == "[2]"
    assert filtered_both[1]["citation_label"] == "[1]"

    # Fallback / unreferenced answer -> zero citations
    filtered_fallback = filter_authoritative_citations(ENGLISH_FALLBACK, authoritative, public_only=True)
    assert len(filtered_fallback) == 0


def test_approved_exact_fallbacks():
    """Verify that exact fallback strings are strictly preserved and uncorrupted."""
    assert ENGLISH_FALLBACK == "Information is not available in the knowledge base."
    assert KANNADA_FALLBACK == "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."
    assert ENGLISH_FALLBACK in SYSTEM_POLICY_ENGLISH
    assert KANNADA_FALLBACK in SYSTEM_POLICY_KANNADA
