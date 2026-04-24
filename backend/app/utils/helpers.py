"""
Shared helper functions.

Provides utility functions for file validation, path management,
and other cross-cutting concerns used across multiple modules.
"""

import os
from pathlib import Path

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)

# Supported file extensions grouped by input modality
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}
SUPPORTED_TEXT_EXTENSIONS = {".txt"}
ALL_SUPPORTED_EXTENSIONS = (
    SUPPORTED_AUDIO_EXTENSIONS | SUPPORTED_PDF_EXTENSIONS | SUPPORTED_TEXT_EXTENSIONS
)


def get_file_extension(filename: str) -> str:
    """
    Extract and normalize the file extension from a filename.

    Args:
        filename: The original filename including extension.

    Returns:
        The lowercase file extension including the dot (e.g., '.pdf').
    """
    return Path(filename).suffix.lower()


def is_supported_file(filename: str) -> bool:
    """
    Check whether a file's extension is in the supported set.

    Args:
        filename: The original filename to validate.

    Returns:
        True if the file extension is supported, False otherwise.
    """
    return get_file_extension(filename) in ALL_SUPPORTED_EXTENSIONS


def detect_file_type(filename: str) -> str:
    """
    Determine the input modality (text, audio, pdf) from a filename.

    Args:
        filename: The original filename.

    Returns:
        One of 'text', 'audio', or 'pdf'.

    Raises:
        ValueError: If the file extension is not supported.
    """
    ext = get_file_extension(filename)

    if ext in SUPPORTED_PDF_EXTENSIONS:
        return "pdf"
    elif ext in SUPPORTED_AUDIO_EXTENSIONS:
        return "audio"
    elif ext in SUPPORTED_TEXT_EXTENSIONS:
        return "text"
    else:
        raise ValueError(
            f"Unsupported file extension: '{ext}'. "
            f"Supported: {', '.join(sorted(ALL_SUPPORTED_EXTENSIONS))}"
        )


def ensure_upload_dir() -> Path:
    """
    Ensure the upload directory exists and return its path.

    Returns:
        Path: The upload directory path.
    """
    settings = get_settings()
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


def generate_safe_filename(original_filename: str, unique_id: str) -> str:
    """
    Generate a safe, unique filename for storage to avoid collisions.

    Args:
        original_filename: The original uploaded filename.
        unique_id: A unique identifier (e.g., document UUID).

    Returns:
        A safe filename in the format '{unique_id}_{original_name}'.
    """
    # Sanitize: keep only alphanumeric, dots, hyphens, underscores
    safe_name = "".join(
        c if c.isalnum() or c in ".-_" else "_"
        for c in original_filename
    )
    return f"{unique_id}_{safe_name}"


def get_file_size_mb(file_path: str | Path) -> float:
    """
    Get the size of a file in megabytes.

    Args:
        file_path: Path to the file.

    Returns:
        File size in MB.
    """
    return os.path.getsize(file_path) / (1024 * 1024)


def truncate_text(text: str, max_length: int = 500) -> str:
    """
    Truncate text to a maximum length, adding an ellipsis if truncated.

    Args:
        text: The text to truncate.
        max_length: Maximum character count.

    Returns:
        The original text if within limits, or a truncated version with '...'.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
