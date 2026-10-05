"""
Unit tests for semantic chunking, page provenance, overlap, and heading detection.
"""

from app.application.knowledge.chunker import (
    chunk_extracted_document,
    split_page_into_chunks,
)
from app.application.knowledge.extractor import ExtractedDocument, ExtractedPage


def test_split_page_into_chunks_with_paragraphs():
    text = (
        "Overview of Badami Caves\n\n"
        "Badami is famous for its rock-cut cave temples dating from the 6th century Chalukya dynasty. "
        "The red sandstone cliffs overlook the serene Agastya Lake.\n\n"
        "Cave 1 is dedicated to Nataraja, depicted with 18 arms demonstrating classical dance postures. "
        "Cave 2 honors Lord Vishnu in his Trivikrama incarnation with one foot reaching the heavens.\n\n"
        "Cave 3 is the largest and most intricately sculpted cave, featuring magnificent reliefs of Narasimha, Varaha, and Harihara. "
        "Cave 4 is a serene Jain temple dedicated to Mahavira."
    )
    page = ExtractedPage(
        page_number=1,
        text=text,
        has_text=True,
        character_count=len(text),
    )

    chunks = split_page_into_chunks(
        page=page,
        document_id="doc-1",
        original_name="badami.pdf",
        start_chunk_index=0,
        target_size=400,
        overlap=60,
    )

    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.document_id == "doc-1"
        assert chunk.page_number == 1
        assert chunk.token_count > 0
        assert chunk.metadata_json["source_filename"] == "badami.pdf"
        assert chunk.metadata_json["page_number"] == 1
        assert len(chunk.chunk_text) >= 40


def test_chunk_extracted_document_multi_page_provenance():
    doc = ExtractedDocument(
        document_id="doc-2",
        original_name="coorg_guide.pdf",
        total_pages=2,
        pages=[
            ExtractedPage(
                page_number=1,
                text="Abbey Falls in Madikeri cascades down lush Western Ghats coffee plantations. It is a prime scenic attraction for nature lovers visiting Kodagu.",
                has_text=True,
                character_count=145,
            ),
            ExtractedPage(
                page_number=2,
                text="Dubare Elephant Camp situated along the sacred Cauvery River offers visitors educational insights into Asian elephant care and river rafting.",
                has_text=True,
                character_count=147,
            ),
        ],
        total_characters=292,
        empty_pages=[],
    )

    chunks = chunk_extracted_document(doc, target_size=800, overlap=120)

    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[0].page_number == 1
    assert "Abbey Falls" in chunks[0].chunk_text

    assert chunks[1].chunk_index == 1
    assert chunks[1].page_number == 2
    assert "Dubare Elephant Camp" in chunks[1].chunk_text


def test_empty_or_tiny_page_produces_no_meaningless_chunks():
    page = ExtractedPage(
        page_number=1,
        text="Tiny text",
        has_text=True,
        character_count=9,
    )
    chunks = split_page_into_chunks(
        page=page,
        document_id="doc-3",
        original_name="tiny.pdf",
        start_chunk_index=0,
    )
    assert len(chunks) == 0
