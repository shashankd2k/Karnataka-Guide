"""
Unit tests for strict PDF multi-layer validation, extension, MIME, magic bytes, size limits, and checksums.
"""

import hashlib
import pytest
from app.application.documents.storage import (
    PayloadTooLargeException,
    sanitize_original_filename,
    validate_pdf_content,
)
from app.core.errors import BadRequestException

VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<\n/Title (Karnataka Tourism Guide)\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"


def test_sanitize_original_filename_valid():
    """Verify standard filename sanitization."""
    assert sanitize_original_filename("Hampi_Guide.pdf") == "Hampi_Guide.pdf"
    assert sanitize_original_filename("Mysore Palace.PDF") == "Mysore Palace.PDF"
    assert sanitize_original_filename("path/to/Badami.pdf") == "Badami.pdf"
    assert sanitize_original_filename("..\\..\\Gokarna.pdf") == "Gokarna.pdf"


def test_sanitize_original_filename_invalid_extension():
    """Verify non-PDF extensions are rejected."""
    with pytest.raises(BadRequestException) as exc_info:
        sanitize_original_filename("malicious_script.exe")
    assert "only .pdf files" in str(exc_info.value.message).lower()


def test_sanitize_original_filename_empty():
    """Verify empty filename is rejected."""
    with pytest.raises(BadRequestException):
        sanitize_original_filename("")
    with pytest.raises(BadRequestException):
        sanitize_original_filename("   ")


def test_validate_pdf_content_success():
    """Verify valid PDF passes all checks and returns correct hash and size."""
    original_name, sha256_hash, file_size = validate_pdf_content(
        raw_filename="Karnataka_Guide.pdf",
        content_type="application/pdf",
        file_bytes=VALID_PDF_BYTES,
        max_bytes=100_000,
    )
    assert original_name == "Karnataka_Guide.pdf"
    assert file_size == len(VALID_PDF_BYTES)
    assert sha256_hash == hashlib.sha256(VALID_PDF_BYTES).hexdigest()


def test_validate_pdf_content_empty_file_rejected():
    """Verify 0-byte file is rejected."""
    with pytest.raises(BadRequestException) as exc_info:
        validate_pdf_content(
            raw_filename="Empty.pdf",
            content_type="application/pdf",
            file_bytes=b"",
            max_bytes=100_000,
        )
    assert "empty" in str(exc_info.value.message).lower()


def test_validate_pdf_content_size_limit_exceeded():
    """Verify file exceeding maximum byte limit raises PayloadTooLargeException (413)."""
    with pytest.raises(PayloadTooLargeException) as exc_info:
        validate_pdf_content(
            raw_filename="Large.pdf",
            content_type="application/pdf",
            file_bytes=VALID_PDF_BYTES,
            max_bytes=10,  # limit lower than file size
        )
    assert exc_info.value.status_code == 413
    assert "exceeds the maximum allowed limit" in str(exc_info.value.message).lower()


def test_validate_pdf_content_invalid_magic_bytes_rejected():
    """Verify fake PDF with text/binary content is rejected even if named .pdf."""
    fake_pdf_bytes = b"Hello, this is just plain text, not a real PDF document."
    with pytest.raises(BadRequestException) as exc_info:
        validate_pdf_content(
            raw_filename="Fake.pdf",
            content_type="application/pdf",
            file_bytes=fake_pdf_bytes,
            max_bytes=100_000,
        )
    assert "invalid file signature" in str(exc_info.value.message).lower()


def test_validate_pdf_content_invalid_mime_rejected():
    """Verify invalid MIME type is rejected."""
    with pytest.raises(BadRequestException) as exc_info:
        validate_pdf_content(
            raw_filename="Doc.pdf",
            content_type="image/jpeg",
            file_bytes=VALID_PDF_BYTES,
            max_bytes=100_000,
        )
    assert "invalid mime type" in str(exc_info.value.message).lower()
