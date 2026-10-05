"""
Unit tests for Multilingual Conversation Engine components.
"""

import pytest
from app.infrastructure.db.models.chat import ChatMessage, SenderType
from app.application.conversation.language_detector import detect_language
from app.application.conversation.context_builder import (
    extract_primary_subject,
    is_follow_up_query,
    resolve_follow_up_query,
)
from app.application.conversation.grounding_guard import (
    ENGLISH_FALLBACK,
    KANNADA_FALLBACK,
    GroundingGuard,
)
from app.application.conversation.citation_formatter import format_citations_and_evidence
from app.application.rag.schemas import RetrievalCandidate


# ==============================================================================
# 1. Language Detector Tests
# ==============================================================================

def test_detect_language_pure_english():
    """Verify standard English sentences are classified as 'en'."""
    res = detect_language("Who built the Chennakeshava Temple at Belur?")
    assert res.language == "en"
    assert res.confidence == 1.0
    assert not res.is_script_mixed
    assert res.kannada_char_count == 0
    assert res.latin_char_count > 0


def test_detect_language_pure_kannada():
    """Verify pure Kannada script queries are classified as 'kn'."""
    res = detect_language("ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿದರು?")
    assert res.language == "kn"
    assert res.confidence == 1.0
    assert not res.is_script_mixed
    assert res.kannada_char_count > 0
    assert res.latin_char_count == 0


def test_detect_language_script_mixed():
    """Verify sentences containing both Kannada and Latin script are classified as 'kn-mixed'."""
    res = detect_language("Belur Chennakeshava ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿದರು?")
    assert res.language == "kn-mixed"
    assert res.is_script_mixed
    assert res.kannada_char_count > 0
    assert res.latin_char_count > 0


def test_detect_language_romanized_kannada_limitation():
    """
    Documented Architectural Boundary:
    Romanized Kannada ('Belur temple yaaru kattidru?') contains only Latin characters
    and is classified as 'en' by the script detector until Phase 11.
    """
    res = detect_language("Belur temple yaaru kattidru?")
    assert res.language == "en"
    assert res.kannada_char_count == 0


def test_detect_language_empty_and_symbols():
    """Verify empty text or symbols default safely to 'kn' per PRD default."""
    res_empty = detect_language("")
    assert res_empty.language == "kn"

    res_symbols = detect_language("12345 !@#$%")
    assert res_symbols.language == "kn"


# ==============================================================================
# 2. Context Builder & Follow-Up Resolver Tests
# ==============================================================================

def test_is_follow_up_query():
    """Test follow-up detection on referential queries and pronouns."""
    assert is_follow_up_query("When was it built?") is True
    assert is_follow_up_query("Who built this?") is True
    assert is_follow_up_query("Why?") is True
    assert is_follow_up_query("Tell me more") is True
    assert is_follow_up_query("ಅದನ್ನು ಯಾರು ಕಟ್ಟಿದರು?") is True
    assert is_follow_up_query("Who commissioned the Belur Chennakeshava temple in 1117 CE?") is False


def test_extract_primary_subject():
    """Test subject extraction from recent chat history."""
    msg1 = ChatMessage(
        id="msg-1",
        session_id="sess-1",
        sender_type=SenderType.USER,
        message_text="Tell me about the Belur Chennakeshava Temple.",
        detected_language="en",
    )
    msg2 = ChatMessage(
        id="msg-2",
        session_id="sess-1",
        sender_type=SenderType.ASSISTANT,
        message_text="The Chennakeshava Temple is a 12th-century Hindu temple in Belur.",
        detected_language="en",
    )
    history = [msg1, msg2]
    subject = extract_primary_subject(history)
    assert subject == "Belur Chennakeshava Temple"


def test_resolve_follow_up_query_pronoun_substitution():
    """Verify pronoun 'it' is substituted with previous subject."""
    msg1 = ChatMessage(
        id="msg-1",
        session_id="sess-1",
        sender_type=SenderType.USER,
        message_text="Who commissioned the Belur Chennakeshava Temple?",
        detected_language="en",
    )
    history = [msg1]

    resolved = resolve_follow_up_query("When was it built?", history)
    assert "Belur Chennakeshava Temple" in resolved
    assert "it" not in resolved.lower()


def test_resolve_follow_up_query_kannada_pronoun():
    """Verify Kannada referential pronoun 'ಅದನ್ನು' is resolved."""
    msg1 = ChatMessage(
        id="msg-1",
        session_id="sess-1",
        sender_type=SenderType.USER,
        message_text="ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯ ಮಾಹಿತಿ ನೀಡಿ",
        detected_language="kn",
    )
    history = [msg1]

    resolved = resolve_follow_up_query("ಅದನ್ನು ಯಾರು ಕಟ್ಟಿದರು?", history)
    assert "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯ" in resolved


def test_resolve_standalone_query_unmodified():
    """Standalone queries with no pronouns should not be altered."""
    msg1 = ChatMessage(
        id="msg-1",
        session_id="sess-1",
        sender_type=SenderType.USER,
        message_text="Tell me about Badami Caves.",
        detected_language="en",
    )
    history = [msg1]

    standalone = "Where is Pattadakal located?"
    resolved = resolve_follow_up_query(standalone, history)
    assert resolved == standalone


# ==============================================================================
# 3. Strict Grounding Guard Tests
# ==============================================================================

def test_grounding_guard_no_active_generation():
    """Verify ungrounded fallback when no active generation exists."""
    guard = GroundingGuard(min_score_threshold=-6.0)
    cand = RetrievalCandidate(
        chunk_id="c-1",
        document_id="d-1",
        source_filename="doc.pdf",
        page_number=1,
        section="Sec",
        text="Some text",
        reranker_score=5.0,
        generation_id="gen-001",
        final_rank=1,
    )
    res_en = guard.evaluate(candidates=[cand], language="en", active_generation_id=None)
    assert not res_en.is_grounded
    assert res_en.fallback_message == ENGLISH_FALLBACK

    res_kn = guard.evaluate(candidates=[cand], language="kn", active_generation_id=None)
    assert not res_kn.is_grounded
    assert res_kn.fallback_message == KANNADA_FALLBACK


def test_grounding_guard_empty_candidates():
    """Verify ungrounded fallback when candidate list is empty."""
    guard = GroundingGuard(min_score_threshold=-6.0)
    res = guard.evaluate(candidates=[], language="en", active_generation_id="gen-123")
    assert not res.is_grounded
    assert res.fallback_message == ENGLISH_FALLBACK
    assert res.evidence_count == 0


def test_grounding_guard_score_below_calibrated_threshold():
    """Verify low Cross-Encoder score triggers ungrounded fallback."""
    guard = GroundingGuard(min_score_threshold=-6.0)
    low_score_cand = RetrievalCandidate(
        chunk_id="c-1",
        document_id="d-1",
        source_filename="doc.pdf",
        page_number=1,
        section="Sec",
        text="Irrelevant text",
        reranker_score=-9.5,
        generation_id="gen-123",
        final_rank=1,
    )
    res = guard.evaluate(candidates=[low_score_cand], language="en", active_generation_id="gen-123")
    assert not res.is_grounded
    assert res.fallback_message == ENGLISH_FALLBACK


def test_grounding_guard_valid_evidence_success():
    """Verify valid evidence passes grounding verification."""
    guard = GroundingGuard(min_score_threshold=-6.0)
    valid_cand = RetrievalCandidate(
        chunk_id="c-1",
        document_id="d-1",
        source_filename="doc.pdf",
        page_number=2,
        section="Architecture",
        text="King Vishnuvardhana commissioned the temple in 1117 CE.",
        reranker_score=8.5,
        generation_id="gen-123",
        final_rank=1,
    )
    res = guard.evaluate(candidates=[valid_cand], language="en", active_generation_id="gen-123")
    assert res.is_grounded
    assert res.fallback_message is None
    assert res.evidence_count == 1
    assert res.top_score == 8.5


# ==============================================================================
# 4. Citation Formatter Tests
# ==============================================================================

def test_format_citations_and_evidence_grounded():
    """Verify structured extractive evidence compilation with citation tokens."""
    cand1 = RetrievalCandidate(
        chunk_id="chunk-abc",
        document_id="doc-xyz",
        source_filename="Belur_Guide.pdf",
        page_number=2,
        section="Commissioning",
        text="Built in 1117 CE by King Vishnuvardhana.",
        reranker_score=9.2,
        generation_id="gen-001",
        final_rank=1,
    )
    cand2 = RetrievalCandidate(
        chunk_id="chunk-def",
        document_id="doc-xyz",
        source_filename="Belur_Guide.pdf",
        page_number=3,
        section="Madanikas",
        text="Features 42 celebrated bracket figures.",
        reranker_score=7.1,
        generation_id="gen-001",
        final_rank=2,
    )
    guard = GroundingGuard()
    g_res = guard.evaluate([cand1, cand2], language="en", active_generation_id="gen-001")

    answer, citations = format_citations_and_evidence([cand1, cand2], g_res, active_generation_id="gen-001")

    assert "[1]" in answer
    assert "[2]" in answer
    assert "Built in 1117 CE by King Vishnuvardhana. [1]" in answer
    assert len(citations) == 2
    assert citations[0]["citation_label"] == "[1]"
    assert citations[0]["chunk_id"] == "chunk-abc"
    assert citations[0]["source_filename"] == "Belur_Guide.pdf"
    assert citations[0]["page_number"] == 2
    assert citations[0]["generation_id"] == "gen-001"


def test_format_citations_and_evidence_ungrounded():
    """Verify ungrounded outcome returns empty citations list."""
    guard = GroundingGuard()
    g_res = guard.evaluate([], language="kn", active_generation_id=None)

    answer, citations = format_citations_and_evidence([], g_res, active_generation_id=None)

    assert answer == KANNADA_FALLBACK
    assert citations == []


# ==============================================================================
# 5. Authoritative Citation Provenance & Consistency Tests
# ==============================================================================

def test_citation_chunk_document_authoritative_consistency():
    """
    Verify all fields in emitted citation dictionaries strictly match
    the authoritative source chunk record without mutation or dropped fields.
    """
    cand = RetrievalCandidate(
        chunk_id="chunk-auth-001",
        document_id="doc-auth-001",
        source_filename="Hampi_Vijayanagara_Guide.pdf",
        page_number=2,
        section="Stone Chariot & Garuda Shrine",
        text="The Stone Chariot is dedicated to Garuda, the vahana of Lord Vishnu.",
        reranker_score=8.75,
        generation_id="gen-auth-999",
        final_rank=1,
    )
    guard = GroundingGuard(min_score_threshold=-6.0)
    g_res = guard.evaluate([cand], language="en", active_generation_id="gen-auth-999")
    
    answer, citations = format_citations_and_evidence([cand], g_res, active_generation_id="gen-auth-999")
    
    assert len(citations) == 1
    cit = citations[0]
    assert cit["chunk_id"] == "chunk-auth-001"
    assert cit["document_id"] == "doc-auth-001"
    assert cit["generation_id"] == "gen-auth-999"
    assert cit["source_filename"] == "Hampi_Vijayanagara_Guide.pdf"
    assert cit["page_number"] == 2
    assert cit["section_header"] == "Stone Chariot & Garuda Shrine"
    assert cit["reranker_score"] == 8.75
    assert cit["citation_label"] == "[1]"


def test_citation_exact_page_provenance():
    """
    Verify page numbers are strictly preserved and never fabricated or defaulted to 0.
    """
    for page in [1, 2, 3, 5, 12]:
        cand = RetrievalCandidate(
            chunk_id=f"chunk-p{page}",
            document_id="doc-page-test",
            source_filename="Aihole_Heritage_Guide.pdf",
            page_number=page,
            section=f"Section on Page {page}",
            text=f"Sample text on page {page}.",
            reranker_score=5.0,
            generation_id="gen-page-test",
            final_rank=1,
        )
        guard = GroundingGuard(min_score_threshold=-6.0)
        g_res = guard.evaluate([cand], language="en", active_generation_id="gen-page-test")
        _, citations = format_citations_and_evidence([cand], g_res, active_generation_id="gen-page-test")
        
        assert len(citations) == 1
        assert citations[0]["page_number"] == page
        assert isinstance(citations[0]["page_number"], int)
        assert citations[0]["page_number"] > 0


def test_citation_generation_consistency():
    """
    Verify citation formatting strictly links citations to the active generation.
    """
    cand = RetrievalCandidate(
        chunk_id="chunk-gen-1",
        document_id="doc-gen-1",
        source_filename="Badami_Caves_Guide.pdf",
        page_number=1,
        section="Overview",
        text="Badami was the regal capital of the Early Chalukyas.",
        reranker_score=7.2,
        generation_id="active-gen-uuid-12345",
        final_rank=1,
    )
    guard = GroundingGuard()
    g_res = guard.evaluate([cand], language="en", active_generation_id="active-gen-uuid-12345")
    _, citations = format_citations_and_evidence([cand], g_res, active_generation_id="active-gen-uuid-12345")
    
    assert len(citations) == 1
    assert citations[0]["generation_id"] == "active-gen-uuid-12345"


def test_citation_no_emission_on_fallback():
    """
    Verify that ungrounded queries (score below threshold or empty candidate list)
    return exactly 0 citations and the appropriate bilingual fallback string.
    """
    guard = GroundingGuard(min_score_threshold=-6.0)
    low_cand = RetrievalCandidate(
        chunk_id="chunk-low",
        document_id="doc-low",
        source_filename="doc.pdf",
        page_number=1,
        section="None",
        text="Random out of domain text",
        reranker_score=-9.8,
        generation_id="gen-1",
        final_rank=1,
    )
    
    # English ungrounded
    g_res_en = guard.evaluate([low_cand], language="en", active_generation_id="gen-1")
    ans_en, cits_en = format_citations_and_evidence([low_cand], g_res_en, active_generation_id="gen-1")
    assert ans_en == ENGLISH_FALLBACK
    assert cits_en == []

    # Kannada ungrounded
    g_res_kn = guard.evaluate([low_cand], language="kn", active_generation_id="gen-1")
    ans_kn, cits_kn = format_citations_and_evidence([low_cand], g_res_kn, active_generation_id="gen-1")
    assert ans_kn == KANNADA_FALLBACK
    assert cits_kn == []


def test_citation_overlapping_chunks_preserve_distinct_pages():
    """
    Verify that overlapping or adjacent chunks spanning consecutive pages
    retain distinct page numbers and do not cross-contaminate page metadata.
    """
    chunk_page1 = RetrievalCandidate(
        chunk_id="chunk-page-1",
        document_id="doc-multi",
        source_filename="Pattadakal_UNESCO_Guide.pdf",
        page_number=1,
        section="Historical Context",
        text="Pattadakal was the holy coronation city on the Malaprabha river.",
        reranker_score=6.5,
        generation_id="gen-multi",
        final_rank=1,
    )
    chunk_page2 = RetrievalCandidate(
        chunk_id="chunk-page-2",
        document_id="doc-multi",
        source_filename="Pattadakal_UNESCO_Guide.pdf",
        page_number=2,
        section="Virupaksha Temple",
        text="Virupaksha Temple was commissioned by Queen Lokamahadevi.",
        reranker_score=6.0,
        generation_id="gen-multi",
        final_rank=2,
    )
    guard = GroundingGuard()
    g_res = guard.evaluate([chunk_page1, chunk_page2], language="en", active_generation_id="gen-multi")
    answer, citations = format_citations_and_evidence([chunk_page1, chunk_page2], g_res, active_generation_id="gen-multi")
    
    assert len(citations) == 2
    assert citations[0]["page_number"] == 1
    assert citations[0]["chunk_id"] == "chunk-page-1"
    assert citations[1]["page_number"] == 2
    assert citations[1]["chunk_id"] == "chunk-page-2"
    assert citations[0]["source_filename"] == citations[1]["source_filename"] == "Pattadakal_UNESCO_Guide.pdf"

