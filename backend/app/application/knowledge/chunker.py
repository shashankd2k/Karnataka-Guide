"""
Deterministic semantic text chunker preserving page provenance, paragraph boundaries, and overlap.
"""

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional
from app.application.knowledge.extractor import ExtractedDocument, ExtractedPage


@dataclass
class ChunkPayload:
    """Prepared chunk data ready for database persistence and embedding."""
    document_id: str
    chunk_index: int
    page_number: int
    section_header: Optional[str]
    chunk_text: str
    token_count: int
    metadata_json: Dict[str, Any]


def _estimate_token_count(text: str) -> int:
    """Heuristic token estimation: ~1.3 tokens per whitespace-separated word."""
    words = len(text.split())
    return max(1, int(words * 1.3))


def _detect_heading(line: str) -> Optional[str]:
    """Detect if a short line likely serves as a section/topic heading."""
    clean = line.strip()
    if 3 <= len(clean) <= 90:
        # Avoid lines ending with sentence punctuation
        if not clean.endswith((".", "?", "!", ",", ";", ":")):
            # Heading candidate
            return clean
        if clean.endswith(":"):
            return clean[:-1].strip()
    return None


def split_page_into_chunks(
    page: ExtractedPage,
    document_id: str,
    original_name: str,
    start_chunk_index: int,
    target_size: int = 800,
    overlap: int = 120,
) -> List[ChunkPayload]:
    """
    Split a single extracted page's text into semantic chunks.
    Prioritizes paragraph breaks, preserves section headers, and applies controlled overlap.
    """
    if not page.has_text or len(page.text.strip()) < 40:
        return []

    paragraphs = [p.strip() for p in page.text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: List[ChunkPayload] = []
    current_chunk_idx = start_chunk_index
    current_text = ""
    current_heading: Optional[str] = None

    for para in paragraphs:
        # Check if paragraph is or starts with a heading
        first_line = para.split("\n")[0]
        detected = _detect_heading(first_line)
        if detected and (len(para) <= 120 or len(para.split("\n")) > 1):
            current_heading = detected

        if not current_text:
            current_text = para
        elif len(current_text) + len(para) + 2 <= target_size:
            current_text += "\n\n" + para
        else:
            # Current chunk has reached capacity
            if len(current_text) >= 40:
                chunks.append(
                    ChunkPayload(
                        document_id=document_id,
                        chunk_index=current_chunk_idx,
                        page_number=page.page_number,
                        section_header=current_heading,
                        chunk_text=current_text,
                        token_count=_estimate_token_count(current_text),
                        metadata_json={
                            "source_filename": original_name,
                            "page_number": page.page_number,
                            "char_count": len(current_text),
                        },
                    )
                )
                current_chunk_idx += 1

            # Compute overlap from previous text
            if len(current_text) > overlap:
                overlap_text = current_text[-overlap:]
                # Align overlap to beginning of word
                space_pos = overlap_text.find(" ")
                if space_pos != -1:
                    overlap_text = overlap_text[space_pos + 1 :]
                current_text = overlap_text + "\n\n" + para
            else:
                current_text = para

    # Flush remaining text
    if len(current_text.strip()) >= 40:
        chunks.append(
            ChunkPayload(
                document_id=document_id,
                chunk_index=current_chunk_idx,
                page_number=page.page_number,
                section_header=current_heading,
                chunk_text=current_text.strip(),
                token_count=_estimate_token_count(current_text.strip()),
                metadata_json={
                    "source_filename": original_name,
                    "page_number": page.page_number,
                    "char_count": len(current_text.strip()),
                },
            )
        )

    return chunks


def chunk_extracted_document(
    doc: ExtractedDocument,
    target_size: int = 800,
    overlap: int = 120,
) -> List[ChunkPayload]:
    """
    Chunk all pages of an extracted document with sequential chunk indices and page provenance.
    """
    all_chunks: List[ChunkPayload] = []
    chunk_index = 0

    for page in doc.pages:
        page_chunks = split_page_into_chunks(
            page=page,
            document_id=doc.document_id,
            original_name=doc.original_name,
            start_chunk_index=chunk_index,
            target_size=target_size,
            overlap=overlap,
        )
        all_chunks.extend(page_chunks)
        chunk_index += len(page_chunks)

    return all_chunks
