"""
Syllabus Filter request/response schemas.

Defines Pydantic models for the two-stage Syllabus Filter pipeline,
including filter execution requests, result responses, and result listings.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class FilterRunRequest(BaseModel):
    """
    Schema for initiating a Syllabus Filter operation.

    Requires either document IDs (for previously uploaded files) or
    raw text content for both the syllabus and notes.
    """

    # Option 1: Reference previously uploaded documents by ID
    syllabus_doc_id: str | None = Field(
        default=None,
        description="ID of a previously uploaded syllabus document.",
    )
    notes_doc_id: str | None = Field(
        default=None,
        description="ID of a previously uploaded notes document.",
    )

    # Option 2: Provide raw text directly
    syllabus_text: str | None = Field(
        default=None,
        max_length=200_000,
        description="Raw syllabus text (alternative to syllabus_doc_id).",
    )
    notes_text: str | None = Field(
        default=None,
        max_length=500_000,
        description="Raw notes text (alternative to notes_doc_id).",
    )

    # Optional configuration
    model: str | None = Field(
        default=None,
        description="Optional LLM model override for this filter operation.",
        examples=["openai/gpt-4o"],
    )


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class FilterResultResponse(BaseModel):
    """Schema for a single Syllabus Filter result."""

    id: str = Field(..., description="Unique result identifier (UUID).")
    user_id: str = Field(..., description="Owner's user ID.")
    syllabus_doc_id: str | None = Field(None, description="Source syllabus document ID.")
    notes_doc_id: str | None = Field(None, description="Source notes document ID.")
    identified_topics: str = Field(
        ...,
        description="Stage 1 output — list of identified syllabus topics.",
    )
    filtered_notes: str = Field(
        ...,
        description="Stage 2 output — notes filtered for syllabus relevance.",
    )
    model_used: str = Field(..., description="LLM model used for processing.")
    processing_time_seconds: float | None = Field(
        None,
        description="Total processing time in seconds.",
    )
    created_at: datetime = Field(..., description="Result creation timestamp.")

    model_config = {"from_attributes": True}


class FilterResultListResponse(BaseModel):
    """Schema for a paginated list of filter results."""

    results: list[FilterResultResponse] = Field(
        ..., description="List of filter result records."
    )
    total: int = Field(..., description="Total number of results.")
    page: int = Field(..., description="Current page number (1-indexed).")
    page_size: int = Field(..., description="Number of items per page.")


class FilterRunResponse(BaseModel):
    """
    Schema for the response after running the Syllabus Filter.

    Contains the full formatted output matching PRD §6.3 format,
    along with the persisted result record.
    """

    result: FilterResultResponse = Field(
        ..., description="The persisted filter result record."
    )
    formatted_output: str = Field(
        ...,
        description=(
            "The complete formatted output with identified topics header "
            "and filtered notes, matching PRD §6.3 output format."
        ),
    )
    message: str = Field(
        default="Syllabus filter completed successfully.",
        description="Status message.",
    )
