"""
Custom exception classes.

Defines application-specific exceptions that map to HTTP status codes.
These are caught by the global exception handler in main.py and converted
into structured JSON error responses.
"""

from fastapi import HTTPException, status


class CodeLensBaseError(Exception):
    """Base exception for all CodeLens application errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# Input & File Errors (4xx)
# ---------------------------------------------------------------------------

class UnsupportedFileTypeError(CodeLensBaseError):
    """
    Raised when a user uploads a file with an unsupported extension.
    Maps to HTTP 400 Bad Request.
    """

    def __init__(self, filename: str, supported_types: list[str] | None = None):
        types_str = ", ".join(supported_types) if supported_types else "pdf, mp3, wav, m4a, ogg, txt"
        message = (
            f"Unsupported file type: '{filename}'. "
            f"Supported formats: {types_str}"
        )
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class EmptyExtractionError(CodeLensBaseError):
    """
    Raised when PDF text extraction yields an empty string.
    This typically occurs with scanned image-based PDFs.
    Maps to HTTP 422 Unprocessable Entity.
    """

    def __init__(self, filename: str):
        message = (
            f"No text could be extracted from '{filename}'. "
            "This may be a scanned/image-based PDF without embedded text. "
            "OCR support is planned for a future release."
        )
        super().__init__(message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class FilterInputError(CodeLensBaseError):
    """
    Raised when the Syllabus Filter is invoked without both required inputs.
    Maps to HTTP 400 Bad Request.
    """

    def __init__(self, detail: str = "Both syllabus and notes content are required."):
        super().__init__(message=detail, status_code=status.HTTP_400_BAD_REQUEST)


class FileTooLargeError(CodeLensBaseError):
    """
    Raised when an uploaded file exceeds the maximum allowed size.
    Maps to HTTP 413 Request Entity Too Large.
    """

    def __init__(self, filename: str, max_size_mb: int):
        message = f"File '{filename}' exceeds the maximum upload size of {max_size_mb} MB."
        super().__init__(message=message, status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)


# ---------------------------------------------------------------------------
# External Service Errors (5xx)
# ---------------------------------------------------------------------------

class TranscriptionError(CodeLensBaseError):
    """
    Raised when audio transcription fails.
    Maps to HTTP 502 Bad Gateway.
    """

    def __init__(self, detail: str = "Audio transcription failed."):
        message = f"Transcription error: {detail}"
        super().__init__(message=message, status_code=status.HTTP_502_BAD_GATEWAY)


class LLMAuthenticationError(CodeLensBaseError):
    """
    Raised when the OpenRouter API rejects the provided API key.
    Maps to HTTP 503 Service Unavailable.
    """

    def __init__(self):
        message = (
            "LLM API authentication failed. Please verify that the "
            "OPENROUTER_API_KEY environment variable is set correctly."
        )
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class LLMRateLimitError(CodeLensBaseError):
    """
    Raised when the OpenRouter API rate limit is exceeded after retries.
    Maps to HTTP 429 Too Many Requests.
    """

    def __init__(self):
        message = (
            "LLM API rate limit exceeded. Maximum retry attempts reached. "
            "Please try again later."
        )
        super().__init__(message=message, status_code=status.HTTP_429_TOO_MANY_REQUESTS)


class LLMResponseError(CodeLensBaseError):
    """
    Raised when the LLM returns an empty or malformed response.
    Maps to HTTP 502 Bad Gateway.
    """

    def __init__(self, detail: str = "The LLM returned an empty or malformed response."):
        message = f"LLM response error: {detail}"
        super().__init__(message=message, status_code=status.HTTP_502_BAD_GATEWAY)


# ---------------------------------------------------------------------------
# Authentication Errors
# ---------------------------------------------------------------------------

class InvalidCredentialsError(HTTPException):
    """Raised when login credentials are invalid."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InactiveUserError(HTTPException):
    """Raised when a deactivated user attempts to authenticate."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact an administrator.",
        )


class InsufficientPermissionsError(HTTPException):
    """Raised when a user lacks the required role for an action."""

    def __init__(self, required_role: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires the '{required_role}' role.",
        )
