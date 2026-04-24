"""
Document ORM model.

Represents uploaded files (PDF, audio, text) and their processing state.
Tracks the original filename, detected type, extracted text content,
and processing status.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from app.database import Base


class FileType(str, enum.Enum):
    """Supported input file types."""
    TEXT = "text"
    AUDIO = "audio"
    PDF = "pdf"


class ProcessingStatus(str, enum.Enum):
    """Document processing status lifecycle."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    """
    Represents an uploaded document in the system.

    Stores metadata about the original file, the extracted text content
    after preprocessing, and the current processing status.

    Attributes:
        id: Unique identifier (UUID).
        user_id: Foreign key to the owning user.
        filename: Original name of the uploaded file.
        file_type: Detected input modality (text, audio, pdf).
        file_path: Server-side storage path for the uploaded file.
        extracted_text: Plain text content after preprocessing.
        status: Current processing state.
        error_message: Error details if processing failed.
        created_at: Timestamp of document creation.
    """

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    file_type: Mapped[FileType] = mapped_column(
        Enum(FileType), nullable=False
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    extracted_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    owner = relationship("User", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status.value})>"
