"""
Syllabus Filter API routes.

Provides endpoints for running the two-stage Syllabus Filter pipeline
and retrieving past filter results.
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.config import get_settings
from app.database import get_db
from app.models.document import Document
from app.models.filter_result import FilterResult
from app.models.user import User
from app.schemas.filter import (
    FilterResultListResponse,
    FilterResultResponse,
    FilterRunRequest,
    FilterRunResponse,
)
from app.services.auth_service import get_current_user
from app.services.syllabus_filter import run_filter
from app.utils.exceptions import FilterInputError

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/filter", tags=["Syllabus Filter"])


@router.post(
    "/run",
    response_model=FilterRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Run the Syllabus Filter",
    description=(
        "Execute the two-stage Syllabus Filter pipeline. Provide either "
        "document IDs (for previously uploaded files) or raw text for both "
        "the syllabus and notes."
    ),
)
async def run_syllabus_filter(
    request: FilterRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FilterRunResponse:
    """
    Run the Syllabus Filter with provided syllabus and notes.

    Supports two input modes:
    1. Document IDs — references previously uploaded and processed documents.
    2. Raw text — provide syllabus and notes text directly.
    """
    syllabus_text = request.syllabus_text
    notes_text = request.notes_text
    syllabus_doc_id = request.syllabus_doc_id
    notes_doc_id = request.notes_doc_id

    # Resolve document IDs to text if provided
    if request.syllabus_doc_id and not syllabus_text:
        result = await db.execute(
            select(Document).where(
                Document.id == request.syllabus_doc_id,
                Document.user_id == current_user.id,
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Syllabus document not found.")
        if not doc.extracted_text:
            raise FilterInputError("Syllabus document has no extracted text.")
        syllabus_text = doc.extracted_text

    if request.notes_doc_id and not notes_text:
        result = await db.execute(
            select(Document).where(
                Document.id == request.notes_doc_id,
                Document.user_id == current_user.id,
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Notes document not found.")
        if not doc.extracted_text:
            raise FilterInputError("Notes document has no extracted text.")
        notes_text = doc.extracted_text

    # Validate that both inputs are available
    if not syllabus_text:
        raise FilterInputError(
            "Syllabus content is required. Provide syllabus_text or syllabus_doc_id."
        )
    if not notes_text:
        raise FilterInputError(
            "Notes content is required. Provide notes_text or notes_doc_id."
        )

    # Run the two-stage filter pipeline in a thread pool
    # (run_filter → send_prompt are synchronous/blocking calls)
    model = request.model
    loop = asyncio.get_event_loop()
    filter_output = await loop.run_in_executor(
        None,
        lambda: run_filter(
            syllabus_text=syllabus_text,
            notes_text=notes_text,
            model=model,
        ),
    )

    # Persist the result
    filter_result = FilterResult(
        user_id=current_user.id,
        syllabus_doc_id=syllabus_doc_id,
        notes_doc_id=notes_doc_id,
        identified_topics=filter_output["identified_topics"],
        filtered_notes=filter_output["filtered_notes"],
        model_used=filter_output["model_used"],
        processing_time_seconds=filter_output["processing_time_seconds"],
    )
    db.add(filter_result)
    await db.flush()
    await db.refresh(filter_result)

    logger.info(
        "filter_completed",
        result_id=filter_result.id,
        user_id=current_user.id,
        processing_time=filter_output["processing_time_seconds"],
    )

    return FilterRunResponse(
        result=FilterResultResponse.model_validate(filter_result),
        formatted_output=filter_output["formatted_output"],
        message="Syllabus filter completed successfully.",
    )


@router.get(
    "/results",
    response_model=FilterResultListResponse,
    summary="List filter results",
    description="Retrieve a paginated list of the current user's past filter results.",
)
async def list_filter_results(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FilterResultListResponse:
    """List all filter results for the current user."""
    count_result = await db.execute(
        select(func.count(FilterResult.id)).where(FilterResult.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(FilterResult)
        .where(FilterResult.user_id == current_user.id)
        .order_by(FilterResult.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    results = result.scalars().all()

    return FilterResultListResponse(
        results=[FilterResultResponse.model_validate(r) for r in results],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/results/{result_id}",
    response_model=FilterResultResponse,
    summary="Get a filter result",
    description="Retrieve a specific filter result by ID.",
)
async def get_filter_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FilterResultResponse:
    """Get a specific filter result by ID (must belong to current user)."""
    result = await db.execute(
        select(FilterResult).where(
            FilterResult.id == result_id,
            FilterResult.user_id == current_user.id,
        )
    )
    filter_result = result.scalar_one_or_none()

    if not filter_result:
        raise HTTPException(status_code=404, detail="Filter result not found.")

    return FilterResultResponse.model_validate(filter_result)


@router.delete(
    "/results/{result_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a filter result",
    description="Delete a specific filter result from the history.",
)
async def delete_filter_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a filter result (must belong to current user)."""
    result = await db.execute(
        select(FilterResult).where(
            FilterResult.id == result_id,
            FilterResult.user_id == current_user.id,
        )
    )
    filter_result = result.scalar_one_or_none()

    if not filter_result:
        raise HTTPException(status_code=404, detail="Filter result not found.")

    await db.delete(filter_result)
    logger.info("filter_result_deleted", result_id=result_id, user_id=current_user.id)
