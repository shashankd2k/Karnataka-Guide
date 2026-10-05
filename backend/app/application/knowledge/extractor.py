"""
PyMuPDF text and page extraction engine with conservative Unicode/NFC normalization.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import unicodedata
import pymupdf as fitz
import structlog
from app.core.errors import BadRequestException

logger = structlog.get_logger(__name__)


@dataclass
class ExtractedPage:
    """Extracted content and metadata for a single PDF page."""
    page_number: int  # 1-indexed
    text: str
    has_text: bool
    character_count: int


@dataclass
class ExtractedDocument:
    """Complete extracted document payload."""
    document_id: str
    original_name: str
    total_pages: int
    pages: List[ExtractedPage]
    total_characters: int
    empty_pages: List[int]


def normalize_text(raw_text: str) -> str:
    """
    Perform conservative text normalization:
    - Standardize Unicode characters to Canonical Decomposition followed by Canonical Composition (NFC)
    - Normalize carriage returns to standard line feeds (\\r\\n -> \\n)
    - Strip trailing spaces from each line without altering historical words or Kannada/Sanskrit glyphs
    - Collapse excessive consecutive newlines (3+ -> 2) to preserve natural paragraph breaks
    """
    if not raw_text:
        return ""

    # Canonical Unicode composition (preserves Indic and diacritical marks)
    text = unicodedata.normalize("NFC", raw_text)

    # Standardize line breaks
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Clean line whitespace
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Collapse excessive line breaks while preserving paragraph boundaries
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    return text.strip()


def extract_pdf_document(
    file_path: Path,
    document_id: str,
    original_name: str,
) -> ExtractedDocument:
    """
    Extract structured text from all pages of a PDF document using PyMuPDF.
    Preserves 1-indexed page provenance, paragraph boundaries, and Unicode characters.
    """
    if not file_path.exists() or not file_path.is_file():
        raise BadRequestException(f"Document file not found at path: {file_path}")

    try:
        doc = fitz.open(str(file_path))
    except Exception as e:
        logger.error("pymupdf_open_failed", path=str(file_path), error=str(e))
        raise BadRequestException(f"Failed to open PDF document with PyMuPDF: {e}")

    extracted_pages: List[ExtractedPage] = []
    empty_pages: List[int] = []
    total_chars = 0

    try:
        total_pages = len(doc)
        for page_idx in range(total_pages):
            page_num = page_idx + 1  # 1-indexed
            page = doc[page_idx]

            # Extract text blocks (tuple: x0, y0, x1, y1, text, block_no, block_type)
            # block_type == 0 indicates text block
            blocks = page.get_text("blocks")
            text_blocks = [b[4] for b in blocks if len(b) > 4 and b[6] == 0 and b[4].strip()]

            raw_page_text = "\n\n".join(text_blocks)
            clean_page_text = normalize_text(raw_page_text)

            has_text = len(clean_page_text) > 0
            char_count = len(clean_page_text)
            total_chars += char_count

            if not has_text:
                empty_pages.append(page_num)
                logger.warning(
                    "pdf_page_has_no_extractable_text",
                    doc_id=document_id,
                    page=page_num,
                    original_name=original_name,
                )

            extracted_pages.append(
                ExtractedPage(
                    page_number=page_num,
                    text=clean_page_text,
                    has_text=has_text,
                    character_count=char_count,
                )
            )

        logger.info(
            "pdf_extraction_completed",
            doc_id=document_id,
            pages=total_pages,
            characters=total_chars,
            empty_pages=len(empty_pages),
        )

        return ExtractedDocument(
            document_id=document_id,
            original_name=original_name,
            total_pages=total_pages,
            pages=extracted_pages,
            total_characters=total_chars,
            empty_pages=empty_pages,
        )

    finally:
        doc.close()
