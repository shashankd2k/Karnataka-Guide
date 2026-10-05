"""
Audio validation and secure temporary file management.
Enforces multi-layer validation: size, extension/MIME allowlist, magic signatures,
container/stream decoding, duration boundaries, and guaranteed cleanup.
"""

from contextlib import asynccontextmanager
import os
from pathlib import Path
import tempfile
from typing import AsyncIterator, Optional, Set, Tuple
import uuid

import av
from fastapi import UploadFile
import structlog

from app.core.config import get_settings
from app.core.errors import AppException

logger = structlog.get_logger(__name__)

# Allowed file extensions and corresponding MIME types
ALLOWED_AUDIO_EXTENSIONS: Set[str] = {".wav", ".mp3", ".ogg", ".webm", ".m4a", ".mp4"}
ALLOWED_AUDIO_MIMES: Set[str] = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/webm",
    "video/webm",  # WebM recorded via browser MediaRecorder is often labeled video/webm
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "video/mp4",
    "application/octet-stream",
}


class AudioValidationError(AppException):
    """Raised when an uploaded audio file fails multi-layer security or decoding validation."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            code="INVALID_AUDIO_PAYLOAD",
            status_code=400,
            details=details or {},
        )


def inspect_magic_bytes(header: bytes, filename: str) -> bool:
    """
    Inspect magic byte signatures for common audio container formats.
    """
    if len(header) < 4:
        return False

    # 1. WAV: RIFF....WAVE
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WAVE":
        return True

    # 2. MP3: ID3 tag or sync frame (0xFF followed by 0xFB, 0xF3, 0xF2, 0xE3)
    if header.startswith(b"ID3"):
        return True
    if len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
        return True

    # 3. OGG: OggS
    if header.startswith(b"OggS"):
        return True

    # 4. WebM/Matroska: EBML header \x1a\x45\xdf\xa3
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return True

    # 5. MP4 / M4A: ....ftyp
    if len(header) >= 8 and header[4:8] == b"ftyp":
        return True

    return False


def validate_and_decode_audio_stream(file_path: Path, max_duration_seconds: float) -> Tuple[float, int, str]:
    """
    Deep decoder validation using PyAV.
    Verifies that the container opens cleanly, contains at least one valid audio stream,
    and does not exceed the duration boundary.

    Returns:
        Tuple of (duration_seconds, sample_rate, codec_name)
    """
    try:
        container = av.open(str(file_path))
    except Exception as e:
        raise AudioValidationError(
            f"Corrupted or unreadable audio container: {str(e)}",
            details={"file_path": file_path.name},
        )

    try:
        audio_streams = [s for s in container.streams if s.type == "audio"]
        if not audio_streams:
            raise AudioValidationError(
                "Uploaded media contains no decodable audio stream (video-only or silent container rejected).",
                details={"streams_found": [s.type for s in container.streams]},
            )

        stream = audio_streams[0]
        codec_name = stream.codec_context.name if stream.codec_context else "unknown"
        sample_rate = stream.codec_context.sample_rate if stream.codec_context else 16000

        # Calculate or estimate duration
        duration_s = 0.0
        if container.duration is not None:
            duration_s = float(container.duration) / float(av.time_base)
        elif stream.duration is not None and stream.time_base is not None:
            duration_s = float(stream.duration * stream.time_base)

        # Enforce maximum duration boundary
        if duration_s > max_duration_seconds:
            raise AudioValidationError(
                f"Audio duration ({duration_s:.1f}s) exceeds maximum allowed limit of {max_duration_seconds:.1f}s.",
                details={"duration_seconds": duration_s, "max_allowed": max_duration_seconds},
            )

        return duration_s, sample_rate, codec_name
    finally:
        container.close()


@asynccontextmanager
async def temp_audio_file_context(upload_file: UploadFile) -> AsyncIterator[Path]:
    """
    Secure temporary file lifecycle manager.
    Validates uploaded file, persists bytes to the transient directory, runs deep decoding checks,
    yields the validated Path, and GUARANTEES cleanup in finally block across all error paths.
    """
    settings = get_settings()
    temp_dir = settings.resolved_temp_audio_path
    filename = upload_file.filename or "audio_upload.wav"
    ext = Path(filename).suffix.lower()

    # 1. Allowlist Extension Check
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise AudioValidationError(
            f"Unsupported audio format '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}",
            details={"filename": filename, "extension": ext},
        )

    # 2. Allowlist Content-Type Check (if provided)
    content_type = upload_file.content_type
    if content_type and content_type.lower() not in ALLOWED_AUDIO_MIMES:
        raise AudioValidationError(
            f"Unsupported audio MIME type '{content_type}'.",
            details={"content_type": content_type},
        )

    # 3. Read and Validate Payload Size
    max_bytes = int(settings.WHISPER_MAX_FILE_SIZE_MB * 1024 * 1024)
    content = await upload_file.read()

    if not content or len(content) == 0:
        raise AudioValidationError("Uploaded audio payload is empty (0 bytes).")

    if len(content) > max_bytes:
        raise AudioValidationError(
            f"Audio payload size ({len(content)} bytes) exceeds maximum limit of {settings.WHISPER_MAX_FILE_SIZE_MB}MB.",
            details={"size_bytes": len(content), "max_bytes": max_bytes},
        )

    # 4. Magic Bytes Signature Verification
    if not inspect_magic_bytes(content[:32], filename):
        raise AudioValidationError(
            f"Audio header signature mismatch for '{ext}'. File does not match expected audio magic bytes.",
            details={"filename": filename},
        )

    # 5. Persist to isolated transient file with unique UUID
    temp_filename = f"stt_{uuid.uuid4().hex[:12]}{ext}"
    temp_file_path = temp_dir / temp_filename

    try:
        temp_file_path.write_bytes(content)

        # 6. Deep Container & Stream Decoder Verification
        validate_and_decode_audio_stream(
            file_path=temp_file_path,
            max_duration_seconds=settings.WHISPER_MAX_AUDIO_SECONDS,
        )

        yield temp_file_path

    finally:
        # Guaranteed Privacy Cleanup: Delete temporary audio file
        try:
            if temp_file_path.exists():
                temp_file_path.unlink(missing_ok=True)
                logger.debug("temporary_audio_cleaned_up", file=temp_file_path.name)
        except Exception as cleanup_err:
            logger.warning("temporary_audio_cleanup_failed", file=temp_file_path.name, error=str(cleanup_err))
