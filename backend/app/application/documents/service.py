"""
Document management application service implementing upload, duplicate detection,
listing, download preparation, failure-safe deletion, and security audit logging.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
import uuid
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from app.application.documents.storage import (
    get_safe_storage_path,
    remove_pdf_from_storage,
    save_pdf_to_storage,
    validate_pdf_content,
)
from app.core.config import get_settings
from app.core.errors import BadRequestException, ConflictException, NotFoundException
from app.infrastructure.db.models.admin import Admin
from app.infrastructure.db.models.audit import AuditLog
from app.infrastructure.db.models.chunk import DocumentChunk
from app.infrastructure.db.models.document import Document, DocumentStatus
from app.infrastructure.db.models.generation import KnowledgeGeneration

logger = structlog.get_logger(__name__)


async def record_audit_event(
    session: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: str,
    admin_id: str,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Helper to persist administrative security audit logs."""
    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        admin_id=admin_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details_json=details or {},
        ip_address=ip_address,
        created_at=datetime.now(timezone.utc),
    )
    session.add(audit_entry)


async def upload_document(
    session: AsyncSession,
    file: Optional[UploadFile] = None,
    current_admin: Admin = None,
    ip_address: Optional[str] = None,
    upload_file: Optional[UploadFile] = None,
) -> Document:
    """
    Handle secure document upload:
    1. Multi-layer validation (filename, extension, MIME, magic bytes, size limits)
    2. Incremental SHA-256 calculation
    3. Duplicate detection against MySQL documents table (returns 409 Conflict if duplicate)
    4. Save PDF to disk with UUID filename (<uuid>.pdf)
    5. Persist Document record in MySQL
    6. Record audit log event
    7. Atomic cleanup of storage file if DB transaction fails
    """
    settings = get_settings()
    doc_id = str(uuid.uuid4())

    target_file = upload_file or file
    if target_file is None:
        raise BadRequestException("No file provided for upload.")

    file_bytes = await target_file.read()

    # Step 1 & 2: Validate file and compute SHA-256
    original_name, sha256_hash, file_size = validate_pdf_content(
        raw_filename=target_file.filename,
        content_type=target_file.content_type,
        file_bytes=file_bytes,
        max_bytes=settings.MAX_PDF_UPLOAD_BYTES,
    )

    # Step 3: Duplicate detection via SHA-256
    existing_stmt = select(Document).where(Document.sha256_hash == sha256_hash)
    existing_doc = (await session.execute(existing_stmt)).scalar_one_or_none()

    if existing_doc:
        logger.warning(
            "document_upload_duplicate_rejected",
            sha256=sha256_hash,
            original_name=original_name,
            existing_doc_id=existing_doc.id,
        )
        await record_audit_event(
            session=session,
            action="DOCUMENT_UPLOAD_DUPLICATE",
            resource_type="DOCUMENT",
            resource_id=existing_doc.id,
            admin_id=current_admin.id,
            details={
                "attempted_filename": original_name,
                "sha256": sha256_hash,
            },
            ip_address=ip_address,
        )
        await session.commit()
        raise ConflictException(
            "A document with identical content (SHA-256) has already been uploaded."
        )

    # Step 4: Write file to storage as <uuid>.pdf
    storage_filename = f"{doc_id}.pdf"
    storage_dir = settings.resolved_storage_path

    save_pdf_to_storage(
        storage_dir=storage_dir,
        file_id=doc_id,
        content=file_bytes,
    )

    # Step 5 & 6: Persist Document record and Audit Log
    new_doc = Document(
        id=doc_id,
        filename=storage_filename,
        original_name=original_name,
        file_size_bytes=file_size,
        sha256_hash=sha256_hash,
        mime_type="application/pdf",
        file_path=str(storage_dir / storage_filename),
        page_count=0,
        status=DocumentStatus.UPLOADED,
        uploaded_by_admin_id=current_admin.id,
    )

    try:
        session.add(new_doc)
        await record_audit_event(
            session=session,
            action="DOCUMENT_UPLOADED",
            resource_type="DOCUMENT",
            resource_id=doc_id,
            admin_id=current_admin.id,
            details={
                "original_name": original_name,
                "file_size_bytes": file_size,
                "sha256": sha256_hash,
            },
            ip_address=ip_address,
        )
        await session.commit()
        await session.refresh(new_doc)
    except Exception as exc:
        # Step 7: Atomic cleanup on DB failure
        logger.error(
            "document_db_insert_failed_cleaning_storage",
            doc_id=doc_id,
            error=str(exc),
        )
        await session.rollback()
        remove_pdf_from_storage(storage_dir, storage_filename)
        raise

    logger.info(
        "document_uploaded_successfully",
        doc_id=new_doc.id,
        original_name=new_doc.original_name,
        size=new_doc.file_size_bytes,
    )
    return new_doc


async def list_documents(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Document], int]:
    """Retrieve paginated list of uploaded documents and total count."""
    count_stmt = select(func.count(Document.id))
    total = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Document)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = (await session.execute(stmt)).scalars().all()
    return list(items), total


async def get_document_metadata(
    session: AsyncSession,
    document_id: str,
) -> Document:
    """Retrieve single document metadata by ID."""
    doc = await session.get(Document, document_id)
    if not doc:
        raise NotFoundException(f"Document with ID '{document_id}' not found.")
    return doc


async def prepare_document_download(
    session: AsyncSession,
    document_id: str,
    current_admin: Admin,
    ip_address: Optional[str] = None,
) -> Tuple[Path, str, str]:
    """
    Verify document existence, resolve physical storage path, and record download audit log.
    Returns (physical_path, original_filename, mime_type).
    """
    settings = get_settings()
    doc = await get_document_metadata(session, document_id)
    target_path = get_safe_storage_path(settings.resolved_storage_path, doc.filename)

    if not target_path.exists() or not target_path.is_file():
        logger.error("document_physical_file_missing", doc_id=document_id, path=str(target_path))
        raise NotFoundException("Document physical file is missing from storage.")

    await record_audit_event(
        session=session,
        action="DOCUMENT_DOWNLOADED",
        resource_type="DOCUMENT",
        resource_id=doc.id,
        admin_id=current_admin.id,
        details={"original_name": doc.original_name},
        ip_address=ip_address,
    )
    await session.commit()

    return target_path, doc.original_name, doc.mime_type


async def delete_document(
    session: AsyncSession,
    document_id: str,
    current_admin: Admin,
    ip_address: Optional[str] = None,
) -> str:
    """
    Failure-safe document deletion:
    1. Verify document existence
    2. Verify document is not referenced by an ACTIVE knowledge generation (returns 409 Conflict if so)
    3. Remove database record and commit (guarantees DB consistency)
    4. Unlink physical storage file
    5. Record audit event
    """
    settings = get_settings()
    doc = await get_document_metadata(session, document_id)
    storage_filename = doc.filename
    original_name = doc.original_name

    # Check if document is referenced by an ACTIVE knowledge generation
    active_gen_check = (
        select(KnowledgeGeneration.generation_version)
        .join(DocumentChunk, DocumentChunk.generation_id == KnowledgeGeneration.id)
        .where(
            DocumentChunk.document_id == document_id,
            KnowledgeGeneration.is_active.is_(True),
        )
        .limit(1)
    )
    active_gen_version = (await session.execute(active_gen_check)).scalar()
    if active_gen_version:
        raise ConflictException(
            f"Cannot delete document '{original_name}' because it is referenced by active knowledge generation '{active_gen_version}'. Deactivate or promote a different generation first."
        )

    # Step 1: Remove DB record and commit transaction
    await session.delete(doc)
    await record_audit_event(
        session=session,
        action="DOCUMENT_DELETED",
        resource_type="DOCUMENT",
        resource_id=document_id,
        admin_id=current_admin.id,
        details={"original_name": original_name},
        ip_address=ip_address,
    )
    await session.commit()

    # Step 2: Unlink physical file from storage safely
    remove_pdf_from_storage(settings.resolved_storage_path, storage_filename)
    logger.info("document_deleted_successfully", doc_id=document_id, original_name=original_name)
    return document_id
