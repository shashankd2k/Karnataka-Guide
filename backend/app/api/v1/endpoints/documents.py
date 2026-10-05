"""
Administrative PDF document management endpoints (/api/v1/admin/documents).
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.auth.dependencies import get_current_admin, require_role
from app.application.documents.schemas import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentResponse,
)
from app.application.documents.service import (
    delete_document,
    get_document_metadata,
    list_documents,
    prepare_document_download,
    upload_document,
)
from app.infrastructure.db.models.admin import Admin, AdminRole
from app.infrastructure.db.session import get_db_session

router = APIRouter()


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Tourism PDF",
    description="Upload and validate a tourism PDF document. Restricted to SUPER_ADMIN and SITE_CURATOR.",
)
async def upload_pdf_document(
    request: Request,
    file: UploadFile = File(..., description="PDF document file (max 50 MB)"),
    current_admin: Admin = Depends(
        require_role(AdminRole.SUPER_ADMIN, AdminRole.SITE_CURATOR)
    ),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """Upload, validate, and store a tourism PDF document."""
    client_ip = request.client.host if request.client else None
    doc = await upload_document(
        session=session,
        upload_file=file,
        current_admin=current_admin,
        ip_address=client_ip,
    )
    return DocumentResponse.model_validate(doc)


@router.get(
    "",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Tourism Documents",
    description="Retrieve paginated list of uploaded tourism documents.",
)
async def get_documents(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page limit"),
    current_admin: Admin = Depends(
        require_role(
            AdminRole.SUPER_ADMIN,
            AdminRole.SITE_CURATOR,
            AdminRole.OPERATOR,
            AdminRole.VIEWER,
        )
    ),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentListResponse:
    """Retrieve paginated list of tourism documents."""
    items, total = await list_documents(session=session, skip=skip, limit=limit)
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Document Metadata",
    description="Retrieve metadata for a specific document by ID.",
)
async def get_document(
    document_id: str,
    current_admin: Admin = Depends(
        require_role(
            AdminRole.SUPER_ADMIN,
            AdminRole.SITE_CURATOR,
            AdminRole.OPERATOR,
            AdminRole.VIEWER,
        )
    ),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """Retrieve document metadata by ID."""
    doc = await get_document_metadata(session=session, document_id=document_id)
    return DocumentResponse.model_validate(doc)


@router.get(
    "/{document_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download Document PDF",
    description="Download the physical PDF file for an existing document.",
)
async def download_document(
    document_id: str,
    request: Request,
    current_admin: Admin = Depends(
        require_role(
            AdminRole.SUPER_ADMIN,
            AdminRole.SITE_CURATOR,
            AdminRole.OPERATOR,
            AdminRole.VIEWER,
        )
    ),
    session: AsyncSession = Depends(get_db_session),
) -> FileResponse:
    """Stream physical PDF document file to authorized administrator."""
    client_ip = request.client.host if request.client else None
    file_path, original_filename, mime_type = await prepare_document_download(
        session=session,
        document_id=document_id,
        current_admin=current_admin,
        ip_address=client_ip,
    )
    return FileResponse(
        path=str(file_path),
        filename=original_filename,
        media_type=mime_type,
    )


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Document",
    description="Safely delete a document and unlink its physical file. Restricted to SUPER_ADMIN and SITE_CURATOR.",
)
async def delete_document_endpoint(
    document_id: str,
    request: Request,
    current_admin: Admin = Depends(
        require_role(AdminRole.SUPER_ADMIN, AdminRole.SITE_CURATOR)
    ),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentDeleteResponse:
    """Safely delete document metadata and storage file."""
    client_ip = request.client.host if request.client else None
    deleted_id = await delete_document(
        session=session,
        document_id=document_id,
        current_admin=current_admin,
        ip_address=client_ip,
    )
    return DocumentDeleteResponse(
        message="Document deleted successfully.",
        document_id=deleted_id,
    )
