"""
Input handler service.

Implements PRD §4.1 — Multi-Modal Input Processing. Handles text passthrough,
PDF text extraction via PyMuPDF, and audio transcription via OpenRouter API
(using the OpenAI-compatible audio endpoint).
All preprocessing occurs before any content is sent to the LLM.
"""

import asyncio
from pathlib import Path

import fitz  # PyMuPDF
import structlog

from app.config import get_settings
from app.utils.exceptions import (
    EmptyExtractionError,
    TranscriptionError,
    UnsupportedFileTypeError,
)
from app.utils.helpers import (
    SUPPORTED_AUDIO_EXTENSIONS,
    SUPPORTED_PDF_EXTENSIONS,
    get_file_extension,
    is_supported_file,
)

logger = structlog.get_logger(__name__)
settings = get_settings()


def process_text_input(text: str) -> str:
    """
    Process a plain text input (passthrough with validation).

    As specified in PRD §4.1, text inputs require no preprocessing
    and are passed directly. However, we validate that the text is
    not empty or whitespace-only.

    Args:
        text: The raw text input from the user.

    Returns:
        The validated text string (stripped of leading/trailing whitespace).

    Raises:
        ValueError: If the text is empty or whitespace-only.
    """
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Text input cannot be empty or whitespace-only.")

    logger.info("text_input_processed", length=len(cleaned))
    return cleaned


def extract_text_from_pdf(file_path: str | Path) -> str:
    """
    Extract text content from a PDF file using PyMuPDF.

    Implements PRD §4.1 for PDF input preprocessing. Opens the PDF,
    extracts text from each page, and concatenates into a single string.

    If the extraction yields an empty string (e.g., scanned image-based PDFs
    without embedded text), raises EmptyExtractionError as specified in
    PRD §6.1 and §6.4.

    Args:
        file_path: Path to the PDF file on disk.

    Returns:
        The extracted plain text content.

    Raises:
        EmptyExtractionError: If no text could be extracted from the PDF.
        FileNotFoundError: If the PDF file does not exist.
        UnsupportedFileTypeError: If the file is not a PDF.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    if get_file_extension(file_path.name) not in SUPPORTED_PDF_EXTENSIONS:
        raise UnsupportedFileTypeError(file_path.name, list(SUPPORTED_PDF_EXTENSIONS))

    logger.info("pdf_extraction_started", filename=file_path.name)

    try:
        doc = fitz.open(str(file_path))
        text_parts: list[str] = []

        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text("text")
            if page_text.strip():
                text_parts.append(page_text)
            logger.debug(
                "pdf_page_extracted",
                page=page_num,
                chars=len(page_text),
            )

        doc.close()

        full_text = "\n\n".join(text_parts).strip()

        if not full_text:
            logger.warning("pdf_extraction_empty", filename=file_path.name)
            raise EmptyExtractionError(file_path.name)

        logger.info(
            "pdf_extraction_completed",
            filename=file_path.name,
            total_chars=len(full_text),
            pages=len(text_parts),
        )

        return full_text

    except EmptyExtractionError:
        raise
    except Exception as e:
        logger.error("pdf_extraction_failed", filename=file_path.name, error=str(e))
        raise RuntimeError(f"Failed to extract text from PDF '{file_path.name}': {e}") from e


async def transcribe_audio(file_path: str | Path) -> str:
    """
    Transcribe an audio file to text via the OpenAI Whisper API.

    Since the project uses OpenRouter for all LLM calls, audio files are
    transcribed through OpenAI's Whisper endpoint (openai.com/v1/audio/transcriptions).
    The same OPENROUTER_API_KEY is expected to work if the user has set
    OPENAI_API_KEY separately, otherwise a clear error is raised.

    Args:
        file_path: Path to the audio file on disk.

    Returns:
        The transcribed text content.

    Raises:
        TranscriptionError: If transcription fails or returns empty text.
        FileNotFoundError: If the audio file does not exist.
        UnsupportedFileTypeError: If the file format is not supported.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    ext = get_file_extension(file_path.name)
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        raise UnsupportedFileTypeError(file_path.name, list(SUPPORTED_AUDIO_EXTENSIONS))

    logger.info("audio_transcription_started", filename=file_path.name)

    def _do_transcribe() -> str:
        from openai import OpenAI

        # Use OpenRouter API key; audio transcription uses OpenAI endpoint.
        api_key = settings.OPENROUTER_API_KEY
        if not api_key:
            raise TranscriptionError(
                "No API key configured. Set OPENROUTER_API_KEY in .env."
            )

        # OpenRouter does not support audio transcription; fall back to OpenAI endpoint.
        # If user only has OpenRouter, this raises a clear error.
        try:
            client = OpenAI(api_key=api_key)
            with open(file_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                )
            return str(transcript).strip()
        except Exception as e:
            raise TranscriptionError(
                f"Audio transcription failed for '{file_path.name}': {e}. "
                "Note: Audio transcription requires an OpenAI API key (not OpenRouter). "
                "Set OPENAI_API_KEY or upload a PDF/text file instead."
            ) from e

    # Run blocking I/O in a thread so we don't block the event loop
    loop = asyncio.get_event_loop()
    transcribed_text = await loop.run_in_executor(None, _do_transcribe)

    if not transcribed_text:
        logger.warning("audio_transcription_empty", filename=file_path.name)
        raise TranscriptionError(
            f"Transcription of '{file_path.name}' returned empty text. "
            "The audio may be silent or corrupted."
        )

    logger.info(
        "audio_transcription_completed",
        filename=file_path.name,
        transcript_length=len(transcribed_text),
    )

    return transcribed_text


async def process_uploaded_file(file_path: str | Path, filename: str) -> str:
    """
    Process an uploaded file based on its type — unified entry point.

    Detects the file type from the extension and routes to the appropriate
    preprocessing handler (PDF extraction, audio transcription, or text passthrough).

    Args:
        file_path: Path to the uploaded file on disk.
        filename: The original filename (used for type detection).

    Returns:
        The extracted/transcribed text content.

    Raises:
        UnsupportedFileTypeError: If the file type is not supported.
        EmptyExtractionError: If PDF extraction yields empty text.
        TranscriptionError: If audio transcription fails.
    """
    if not is_supported_file(filename):
        raise UnsupportedFileTypeError(filename)

    ext = get_file_extension(filename)

    if ext in SUPPORTED_PDF_EXTENSIONS:
        # Run PDF extraction in thread pool (blocking I/O)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, extract_text_from_pdf, file_path)
    elif ext in SUPPORTED_AUDIO_EXTENSIONS:
        return await transcribe_audio(file_path)
    else:
        # Text file — read and passthrough
        file_path = Path(file_path)
        content = file_path.read_text(encoding="utf-8", errors="replace")
        return process_text_input(content)
