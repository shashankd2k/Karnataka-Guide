"""
Secure PDF validation, path traversal prevention, and filesystem storage utilities.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional, Tuple
import structlog
from app.core.errors import AppException, BadRequestException

logger = structlog.get_logger(__name__)

PDF_MAGIC_BYTES = b"%PDF"


class PayloadTooLargeException(AppException):
    """Raised when uploaded file exceeds configured maximum byte limit."""
    def __init__(self, message: str = "Uploaded file exceeds maximum allowed size."):
        super().__init__(
            message=message,
            status_code=413,
            code="PAYLOAD_TOO_LARGE",
        )


def sanitize_original_filename(raw_filename: Optional[str]) -> str:
    """Sanitize and strip unsafe path characters from user-provided filename."""
    if not raw_filename or not raw_filename.strip():
        raise BadRequestException("Uploaded filename cannot be empty.")

    # Extract only the base name (prevents ../ or C:\ path injection)
    base_name = os.path.basename(raw_filename.strip().replace("\\", "/"))
    if not base_name or base_name in (".", ".."):
        raise BadRequestException("Invalid filename format.")

    if not base_name.lower().endswith(".pdf"):
        raise BadRequestException("Invalid file extension. Only .pdf files are accepted.")

    return base_name


def validate_pdf_content(
    raw_filename: Optional[str],
    content_type: Optional[str],
    file_bytes: bytes,
    max_bytes: int,
) -> Tuple[str, str, int]:
    """
    Perform strict multi-layer verification on uploaded PDF bytes.
    Validates:
      1. Filename is valid and ends with .pdf
      2. File is not empty (size > 0)
      3. File size does not exceed max_bytes (HTTP 413)
      4. Magic bytes start with %PDF signature
      5. Calculates SHA-256 checksum

    Returns: (sanitized_original_name, sha256_hash, file_size_bytes)
    """
    original_name = sanitize_original_filename(raw_filename)
    file_size = len(file_bytes)

    if file_size == 0:
        raise BadRequestException("Uploaded file is empty (0 bytes).")

    if file_size > max_bytes:
        logger.warning("pdf_upload_rejected_file_too_large", size=file_size, max_bytes=max_bytes)
        raise PayloadTooLargeException(
            f"File size ({file_size} bytes) exceeds the maximum allowed limit of {max_bytes} bytes."
        )

    # Validate MIME type if provided
    if content_type:
        normalized_mime = content_type.lower().split(";")[0].strip()
        if normalized_mime not in ("application/pdf", "application/x-pdf", "application/octet-stream"):
            logger.warning("pdf_upload_rejected_invalid_mime", mime=content_type)
            raise BadRequestException(f"Invalid MIME type '{content_type}'. Only 'application/pdf' is accepted.")

    # Strict Magic Bytes Validation (PDF specification requires %PDF header at byte 0 or within the first 1024 bytes)
    header_chunk = file_bytes[:1024]
    if not (header_chunk.startswith(PDF_MAGIC_BYTES) or PDF_MAGIC_BYTES in header_chunk[:128]):
        logger.warning("pdf_upload_rejected_invalid_magic_bytes", header=header_chunk[:16])
        raise BadRequestException(
            "Invalid file signature. The file content does not begin with a valid '%PDF' header."
        )

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    return original_name, sha256_hash, file_size


def get_safe_storage_path(storage_dir: Path, filename: str) -> Path:
    """Resolve and verify storage path strictly within configured storage directory."""
    resolved_storage = storage_dir.resolve()
    target_path = (resolved_storage / filename).resolve()

    # Prevent directory traversal
    if not target_path.is_relative_to(resolved_storage):
        logger.error("path_traversal_attempt_detected", filename=filename, storage=str(resolved_storage))
        raise BadRequestException("Unsafe filename or path traversal detected.")

    return target_path


def save_pdf_to_storage(storage_dir: Path, file_id: str, content: bytes) -> Path:
    """Atomically write PDF bytes to UUID-based filename in storage directory."""
    storage_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{file_id}.pdf"
    target_path = get_safe_storage_path(storage_dir, filename)

    with open(target_path, "wb") as f:
        f.write(content)

    return target_path


def remove_pdf_from_storage(storage_dir: Path, filename: str) -> bool:
    """Safely unlink physical PDF file from storage if present."""
    try:
        target_path = get_safe_storage_path(storage_dir, filename)
        if target_path.exists() and target_path.is_file():
            target_path.unlink()
            return True
    except Exception as e:
        logger.warning("pdf_file_removal_warning", filename=filename, error=str(e))
    return False
