"""
Documents API routes.

Provides endpoints for uploading files (PDF, audio), submitting text
for LLM processing, and managing uploaded documents.
"""

import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.config import get_settings
from app.database import get_db
from app.models.document import Document, FileType, ProcessingStatus
from app.models.user import User
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    TextProcessRequest,
    TextProcessResponse,
)
from app.services.auth_service import get_current_user
from app.services.input_handler import process_uploaded_file
from app.services.llm_client import send_prompt
from app.utils.exceptions import UnsupportedFileTypeError
from app.utils.helpers import (
    detect_file_type,
    ensure_upload_dir,
    generate_safe_filename,
    is_supported_file,
)

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a file",
    description="Upload a PDF or audio file. The file is saved, text is extracted, and a document record is created.",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF or audio file to upload"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentUploadResponse:
    """Upload a file, extract text, and create a document record."""
    filename = file.filename or "unknown"

    # Validate file type
    if not is_supported_file(filename):
        raise UnsupportedFileTypeError(filename)

    # Detect file type
    file_type_str = detect_file_type(filename)
    file_type = FileType(file_type_str)

    # Create document record
    doc = Document(
        user_id=current_user.id,
        filename=filename,
        file_type=file_type,
        status=ProcessingStatus.PROCESSING,
    )
    db.add(doc)
    await db.flush()

    # Save file to disk
    upload_dir = ensure_upload_dir()
    safe_name = generate_safe_filename(filename, doc.id)
    file_path = upload_dir / safe_name

    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        doc.file_path = str(file_path)
    except Exception as e:
        doc.status = ProcessingStatus.FAILED
        doc.error_message = f"Failed to save file: {e}"
        await db.flush()
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Extract text (runs blocking IO in thread pool via process_uploaded_file)
    try:
        extracted_text = await process_uploaded_file(str(file_path), filename)
        doc.extracted_text = extracted_text
        doc.status = ProcessingStatus.COMPLETED
    except Exception as e:
        doc.status = ProcessingStatus.FAILED
        doc.error_message = str(e)
        logger.error("document_processing_failed", doc_id=doc.id, error=str(e))

    await db.flush()
    await db.refresh(doc)

    logger.info("document_uploaded", doc_id=doc.id, filename=filename, status=doc.status.value)

    return DocumentUploadResponse(
        document=DocumentResponse.model_validate(doc),
        message=f"File '{filename}' uploaded. Status: {doc.status.value}.",
    )


@router.post(
    "/process-text",
    response_model=TextProcessResponse,
    summary="Process text with the LLM",
    description="Submit plain text for processing by the LLM and receive the response.",
)
async def process_text(
    request: TextProcessRequest,
    current_user: User = Depends(get_current_user),
) -> TextProcessResponse:
    """Send text to the LLM and return the response."""
    system = request.system_prompt or "You are a helpful academic assistant."
    model = request.model or settings.DEFAULT_MODEL

    # Run blocking LLM call in thread pool
    loop = asyncio.get_event_loop()
    response_text = await loop.run_in_executor(
        None,
        lambda: send_prompt(
            user_prompt=request.text,
            system_prompt=system,
            model=model,
        ),
    )

    logger.info("text_processed", user_id=current_user.id, model=model)

    return TextProcessResponse(
        input_text=request.text,
        response=response_text,
        model_used=model,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List user's documents",
    description="Retrieve a paginated list of the current user's uploaded documents.",
)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    """List all documents belonging to the current user."""
    # Count total
    count_result = await db.execute(
        select(func.count(Document.id)).where(Document.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    description="Retrieve details and extracted text of a specific document.",
)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Get a specific document by ID (must belong to current user)."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    return DocumentResponse.model_validate(doc)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description="Delete a document and its associated file from storage.",
)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document (must belong to current user)."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Delete file from disk if it exists
    if doc.file_path:
        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()

    await db.delete(doc)
    logger.info("document_deleted", doc_id=document_id, user_id=current_user.id)
