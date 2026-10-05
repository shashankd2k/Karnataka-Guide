"""
Unit tests for PyMuPDF text extraction, Unicode normalization, and empty page handling.
"""

from pathlib import Path
import pymupdf as fitz
import pytest
from app.application.knowledge.extractor import (
    extract_pdf_document,
    normalize_text,
)
from app.core.errors import BadRequestException


def _create_test_pdf(
    file_path: Path,
    pages_content: list[str],
) -> Path:
    """Helper to generate physical test PDFs with specific page contents."""
    doc = fitz.open()
    for text in pages_content:
        page = doc.new_page()
        if text.strip():
            page.insert_text((50, 72), text, fontsize=11)
    doc.save(str(file_path))
    doc.close()
    return file_path


def test_normalize_text_preserves_unicode_and_cleans_breaks():
    raw = "ಮೈಸೂರು ಅರಮನೆ \r\n\r\n\r\n\r\nHeritage  Palace  \n\n\n\nKarnataka Tourism"
    normalized = normalize_text(raw)
    assert "ಮೈಸೂರು ಅರಮನೆ" in normalized
    assert "\r" not in normalized
    assert "\n\n\n" not in normalized
    assert "Heritage Palace" in normalized or "Heritage  Palace" in normalized


def test_extract_pdf_document_multi_page(tmp_path: Path):
    pdf_file = tmp_path / "karnataka_heritage.pdf"
    pages = [
        "Mysore Palace: The royal residence of the Wadiyar dynasty.",
        "Hampi: UNESCO World Heritage site featuring Vijayanagara architecture.",
        "Gokarna: Coastal paradise with Om Beach and Mahabaleshwara temple.",
    ]
    _create_test_pdf(pdf_file, pages)

    extracted = extract_pdf_document(
        file_path=pdf_file,
        document_id="doc-123",
        original_name="karnataka_heritage.pdf",
    )

    assert extracted.document_id == "doc-123"
    assert extracted.total_pages == 3
    assert len(extracted.pages) == 3
    assert len(extracted.empty_pages) == 0
    assert extracted.pages[0].page_number == 1
    assert "Mysore Palace" in extracted.pages[0].text
    assert extracted.pages[1].page_number == 2
    assert "Hampi" in extracted.pages[1].text
    assert extracted.pages[2].page_number == 3
    assert "Gokarna" in extracted.pages[2].text


def test_extract_pdf_with_empty_pages(tmp_path: Path):
    pdf_file = tmp_path / "mixed_pages.pdf"
    pages = [
        "Valid text on page one.",
        "",  # Empty page
        "Valid text on page three.",
    ]
    _create_test_pdf(pdf_file, pages)

    extracted = extract_pdf_document(
        file_path=pdf_file,
        document_id="doc-456",
        original_name="mixed_pages.pdf",
    )

    assert extracted.total_pages == 3
    assert 2 in extracted.empty_pages
    assert extracted.pages[1].has_text is False
    assert extracted.pages[0].has_text is True
    assert extracted.pages[2].has_text is True


def test_extract_nonexistent_pdf_raises_bad_request(tmp_path: Path):
    missing_file = tmp_path / "nonexistent.pdf"
    with pytest.raises(BadRequestException):
        extract_pdf_document(
            file_path=missing_file,
            document_id="doc-999",
            original_name="nonexistent.pdf",
        )
