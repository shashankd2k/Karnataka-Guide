"""
Unit and integration tests for RAG Hybrid Retrieval (Normalization, BM25, Dense, RRF, Cross-Encoder, Filters).
"""

from unittest.mock import MagicMock, patch
import pytest
from app.application.rag.normalization import normalize_query_for_search, tokenize_for_bm25
from app.application.rag.bm25 import BM25CorpusItem, BM25GenerationIndex
from app.application.rag.dense import retrieve_dense_candidates
from app.application.rag.fusion import reciprocal_rank_fusion
from app.application.rag.reranker import rerank_candidates
from app.application.rag.filters import (
    filter_noise_chunks,
    is_bibliography_or_noise,
    suppress_duplicate_chunks,
)
from app.application.rag.schemas import RetrievalCandidate


def test_normalization_unicode_and_diacritics():
    """Verify IAST diacritic normalization and Kannada Unicode preservation."""
    # IAST diacritics mapping
    assert normalize_query_for_search("Chennakēśava") == "Chennakeshava"
    assert normalize_query_for_search("Hoysaḷa Kēśava") == "Hoysala Keshava"
    assert normalize_query_for_search("Kṛṣṇa Śiva Chāḷukya") == "Krishna Shiva Chalukya"
    
    # Kannada Unicode preservation
    kannada_query = "ಬೇಲೂರು ಚನ್ನಕೇಶವ ದೇವಾಲಯ"
    assert normalize_query_for_search(kannada_query) == kannada_query
    
    # BM25 tokenization
    tokens_en = tokenize_for_bm25("Chennakēśava Temple at Belur, 1117 CE!")
    assert "chennakeshava" in tokens_en
    assert "temple" in tokens_en
    assert "belur" in tokens_en
    assert "1117" in tokens_en
    
    tokens_kn = tokenize_for_bm25(kannada_query)
    assert "ಬೇಲೂರು" in tokens_kn
    assert "ಚನ್ನಕೇಶವ" in tokens_kn


def test_bm25_indexing_and_scoring():
    """Verify BM25 corpus indexing and keyword ranking."""
    items = [
        BM25CorpusItem(
            chunk_id="c1",
            document_id="d1",
            generation_id="g1",
            text="The Chennakeshava Temple at Belur was built by King Vishnuvardhana.",
            page_number=1,
            section="History",
            source_filename="belur.pdf",
            metadata_json={},
        ),
        BM25CorpusItem(
            chunk_id="c2",
            document_id="d1",
            generation_id="g1",
            text="Halebidu Hoysaleswara temple features magnificent soapstone sculptures.",
            page_number=2,
            section="Art",
            source_filename="belur.pdf",
            metadata_json={},
        ),
        BM25CorpusItem(
            chunk_id="c3",
            document_id="d2",
            generation_id="g1",
            text="Pattadakal Virupaksha temple reflects early Chalukyan temple architecture.",
            page_number=1,
            section="Architecture",
            source_filename="pattadakal.pdf",
            metadata_json={},
        ),
    ]

    index = BM25GenerationIndex(generation_id="g1", items=items)
    results = index.query("Vishnuvardhana Belur", top_k=2)

    assert len(results) >= 1
    assert results[0].chunk_id == "c1"
    assert results[0].bm25_rank == 1
    assert results[0].bm25_score > 0.0


def test_reciprocal_rank_fusion():
    """Verify RRF merges dense and sparse rankings with standard k=60."""
    dense_candidates = [
        RetrievalCandidate(
            chunk_id="c1",
            document_id="d1",
            generation_id="g1",
            text="Text 1",
            page_number=1,
            source_filename="doc1.pdf",
            dense_rank=1,
            dense_score=0.9,
            final_rank=1,
        ),
        RetrievalCandidate(
            chunk_id="c2",
            document_id="d1",
            generation_id="g1",
            text="Text 2",
            page_number=2,
            source_filename="doc1.pdf",
            dense_rank=2,
            dense_score=0.7,
            final_rank=2,
        ),
    ]

    bm25_candidates = [
        RetrievalCandidate(
            chunk_id="c2",
            document_id="d1",
            generation_id="g1",
            text="Text 2",
            page_number=2,
            source_filename="doc1.pdf",
            bm25_rank=1,
            bm25_score=12.5,
            final_rank=1,
        ),
        RetrievalCandidate(
            chunk_id="c3",
            document_id="d2",
            generation_id="g1",
            text="Text 3",
            page_number=1,
            source_filename="doc2.pdf",
            bm25_rank=2,
            bm25_score=8.0,
            final_rank=2,
        ),
    ]

    fused = reciprocal_rank_fusion(dense_candidates, bm25_candidates, k=60, top_n=3)

    assert len(fused) == 3
    # c2 is rank 2 in dense (1/62) + rank 1 in bm25 (1/61) = 0.016129 + 0.016393 = ~0.0325
    # c1 is rank 1 in dense (1/61) + absent = 0.016393
    # c3 is rank 2 in bm25 (1/62) + absent = 0.016129
    assert fused[0].chunk_id == "c2"
    assert fused[0].final_rank == 1
    assert fused[0].dense_rank == 2
    assert fused[0].bm25_rank == 1

    assert fused[1].chunk_id == "c1"
    assert fused[2].chunk_id == "c3"


def test_cross_encoder_reranking_with_mock():
    """Verify Cross-Encoder reorders candidates based on relevance prediction."""
    candidates = [
        RetrievalCandidate(
            chunk_id="c1",
            document_id="d1",
            generation_id="g1",
            text="Unrelated text about modern highways.",
            page_number=1,
            source_filename="doc1.pdf",
            rrf_score=0.030,
            final_rank=1,
        ),
        RetrievalCandidate(
            chunk_id="c2",
            document_id="d1",
            generation_id="g1",
            text="King Vishnuvardhana commissioned the Belur Chennakeshava Temple.",
            page_number=2,
            source_filename="doc1.pdf",
            rrf_score=0.025,
            final_rank=2,
        ),
    ]

    mock_model = MagicMock()
    # Return lower score for c1, higher score for c2
    mock_model.predict.return_value = [-2.5, 8.4]

    with patch("app.application.rag.reranker.get_cross_encoder_model", return_value=mock_model):
        reranked = rerank_candidates("Who built Belur temple?", candidates)

    assert len(reranked) == 2
    assert reranked[0].chunk_id == "c2"
    assert reranked[0].reranker_score == 8.4
    assert reranked[0].final_rank == 1
    assert reranked[1].chunk_id == "c1"
    assert reranked[1].reranker_score == -2.5
    assert reranked[1].final_rank == 2


def test_noise_and_bibliography_filtering():
    """Verify suppression of bibliography and table-of-contents chunks."""
    c_content = RetrievalCandidate(
        chunk_id="c1",
        document_id="d1",
        generation_id="g1",
        text="The star-shaped plinth (jagati) supports the soapstone sanctum.",
        page_number=3,
        section="Architecture",
        source_filename="belur.pdf",
        final_rank=1,
    )
    c_bib_section = RetrievalCandidate(
        chunk_id="c2",
        document_id="d1",
        generation_id="g1",
        text="[1] Hardy, Adam. Indian Temple Architecture. 1995.",
        page_number=10,
        section="Selected Bibliography",
        source_filename="belur.pdf",
        final_rank=2,
    )
    c_bib_text = RetrievalCandidate(
        chunk_id="c3",
        document_id="d1",
        generation_id="g1",
        text="[1] Foekema, Gerard. Hoysala Architecture, pp. 45-60. Archaeological Survey of India. ISBN: 978-81-7017-353-3.",
        page_number=11,
        section="Appendix",
        source_filename="belur.pdf",
        final_rank=3,
    )
    c_toc = RetrievalCandidate(
        chunk_id="c4",
        document_id="d1",
        generation_id="g1",
        text="Chapter 1: History ......... 5\nChapter 2: Sculptures ........ 12\nChapter 3: Epigraphy ........ 25",
        page_number=1,
        section="Contents",
        source_filename="belur.pdf",
        final_rank=4,
    )

    assert is_bibliography_or_noise(c_content) is False
    assert is_bibliography_or_noise(c_bib_section) is True
    assert is_bibliography_or_noise(c_bib_text) is True
    assert is_bibliography_or_noise(c_toc) is True

    filtered = filter_noise_chunks([c_content, c_bib_section, c_bib_text, c_toc], query_text="What is the plinth shape?")
    assert len(filtered) == 1
    assert filtered[0].chunk_id == "c1"


def test_duplicate_chunk_suppression():
    """Verify deduplication of identical IDs and adjacent chunks with high lexical overlap."""
    c1 = RetrievalCandidate(
        chunk_id="c1",
        document_id="d1",
        generation_id="g1",
        text="The Chennakeshava temple is dedicated to Lord Vishnu and stands inside a walled complex.",
        page_number=2,
        source_filename="belur.pdf",
        final_rank=1,
    )
    # Duplicate ID
    c1_dup = c1.model_copy()
    c1_dup.final_rank = 2

    # High lexical overlap on same page
    c2_overlap = RetrievalCandidate(
        chunk_id="c2",
        document_id="d1",
        generation_id="g1",
        text="The Chennakeshava temple is dedicated to Lord Vishnu and stands proudly inside a walled complex.",
        page_number=2,
        source_filename="belur.pdf",
        final_rank=3,
    )
    # Distinct chunk
    c3_distinct = RetrievalCandidate(
        chunk_id="c3",
        document_id="d1",
        generation_id="g1",
        text="Darpana Sundari is the most celebrated bracket figure in the temple.",
        page_number=4,
        source_filename="belur.pdf",
        final_rank=4,
    )

    suppressed = suppress_duplicate_chunks([c1, c1_dup, c2_overlap, c3_distinct])
    assert len(suppressed) == 2
    assert suppressed[0].chunk_id == "c1"
    assert suppressed[0].final_rank == 1
    assert suppressed[1].chunk_id == "c3"
    assert suppressed[1].final_rank == 2
