"""
Unit tests for filesystem storage security, path traversal prevention, and cleanup.
"""

from pathlib import Path
import pytest
from app.application.documents.storage import (
    get_safe_storage_path,
    remove_pdf_from_storage,
    save_pdf_to_storage,
)
from app.core.config import get_settings
from app.core.errors import BadRequestException


def test_stable_storage_path_resolution():
    """Verify storage path resolves from stable application base directory."""
    settings = get_settings()
    path = settings.resolved_storage_path
    assert path.is_absolute()
    assert path.name == "documents"


def test_save_and_remove_pdf_from_storage(tmp_path: Path):
    """Verify saving file to disk and safe removal."""
    file_id = "test-doc-uuid-12345"
    content = b"%PDF-1.4 sample content"

    saved_path = save_pdf_to_storage(
        storage_dir=tmp_path,
        file_id=file_id,
        content=content,
    )
    assert saved_path.exists()
    assert saved_path.is_file()
    assert saved_path.name == f"{file_id}.pdf"
    assert saved_path.read_bytes() == content

    # Test safe removal
    removed = remove_pdf_from_storage(tmp_path, f"{file_id}.pdf")
    assert removed is True
    assert not saved_path.exists()

    # Re-removing missing file returns False without error
    assert remove_pdf_from_storage(tmp_path, f"{file_id}.pdf") is False


def test_path_traversal_prevention(tmp_path: Path):
    """Verify attempts to escape storage directory raise BadRequestException."""
    with pytest.raises(BadRequestException) as exc_info:
        get_safe_storage_path(tmp_path, "../../system32/cmd.exe")
    assert "path traversal" in str(exc_info.value.message).lower()
