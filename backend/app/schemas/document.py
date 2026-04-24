"""
Document request/response schemas.

Defines Pydantic models for file upload responses, document listings,
and text processing requests.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.document import FileType, ProcessingStatus


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class TextProcessRequest(BaseModel):
    """Schema for submitting plain text for LLM processing."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=100_000,
        description="The plain text content to process via the LLM.",
        examples=["Explain the concept of polymorphism in object-oriented programming."],
    )
    model: str | None = Field(
        default=None,
        description="Optional LLM model override. Uses the default model if not specified.",
        examples=["openai/gpt-4o"],
    )
    system_prompt: str | None = Field(
        default=None,
        description="Optional system prompt to guide the LLM's behavior.",
        examples=["You are a helpful academic tutor."],
    )


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class DocumentResponse(BaseModel):
    """Schema for a single document's details."""

    id: str = Field(..., description="Unique document identifier (UUID).")
    user_id: str = Field(..., description="Owner's user ID.")
    filename: str = Field(..., description="Original uploaded filename.")
    file_type: FileType = Field(..., description="Detected file type.")
    extracted_text: str | None = Field(None, description="Extracted text content (if processed).")
    status: ProcessingStatus = Field(..., description="Current processing status.")
    error_message: str | None = Field(None, description="Error details if processing failed.")
    created_at: datetime = Field(..., description="Upload timestamp.")

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Schema for a paginated list of documents."""

    documents: list[DocumentResponse] = Field(
        ..., description="List of document records."
    )
    total: int = Field(..., description="Total number of documents.")
    page: int = Field(..., description="Current page number (1-indexed).")
    page_size: int = Field(..., description="Number of items per page.")


class TextProcessResponse(BaseModel):
    """Schema for the LLM's response to a text processing request."""

    input_text: str = Field(..., description="The original input text.")
    response: str = Field(..., description="The LLM-generated response.")
    model_used: str = Field(..., description="The model that generated the response.")


class DocumentUploadResponse(BaseModel):
    """Schema for the response after uploading and processing a file."""

    document: DocumentResponse = Field(..., description="The created document record.")
    message: str = Field(
        default="File uploaded and processing started.",
        description="Status message.",
    )
