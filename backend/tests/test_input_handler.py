"""
Input handler service tests.

Tests PDF text extraction, text passthrough validation,
file type detection, and error handling.
"""

import os
import tempfile
from pathlib import Path

import pytest

from app.services.input_handler import (
    extract_text_from_pdf,
    process_text_input,
)
from app.utils.exceptions import EmptyExtractionError, UnsupportedFileTypeError
from app.utils.helpers import detect_file_type, is_supported_file


# ---------------------------------------------------------------------------
# Text passthrough tests
# ---------------------------------------------------------------------------

def test_process_text_input_valid():
    """Test valid text is returned stripped."""
    result = process_text_input("  Hello, world!  ")
    assert result == "Hello, world!"


def test_process_text_input_empty():
    """Test empty text raises ValueError."""
    with pytest.raises(ValueError, match="empty"):
        process_text_input("")


def test_process_text_input_whitespace():
    """Test whitespace-only text raises ValueError."""
    with pytest.raises(ValueError, match="empty"):
        process_text_input("   \n\t  ")


# ---------------------------------------------------------------------------
# File type detection tests
# ---------------------------------------------------------------------------

def test_detect_pdf():
    assert detect_file_type("syllabus.pdf") == "pdf"


def test_detect_audio_mp3():
    assert detect_file_type("lecture.mp3") == "audio"


def test_detect_audio_wav():
    assert detect_file_type("recording.wav") == "audio"


def test_detect_audio_m4a():
    assert detect_file_type("voice.m4a") == "audio"


def test_detect_audio_ogg():
    assert detect_file_type("audio.ogg") == "audio"


def test_detect_text():
    assert detect_file_type("notes.txt") == "text"


def test_detect_unsupported():
    with pytest.raises(ValueError, match="Unsupported"):
        detect_file_type("document.docx")


def test_is_supported_pdf():
    assert is_supported_file("test.pdf") is True


def test_is_supported_mp3():
    assert is_supported_file("test.mp3") is True


def test_is_supported_docx():
    assert is_supported_file("test.docx") is False


def test_is_supported_exe():
    assert is_supported_file("virus.exe") is False


# ---------------------------------------------------------------------------
# PDF extraction tests
# ---------------------------------------------------------------------------

def test_extract_pdf_file_not_found():
    """Test extraction raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        extract_text_from_pdf("/nonexistent/path/file.pdf")


def test_extract_pdf_wrong_extension():
    """Test extraction rejects non-PDF files."""
    f = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    try:
        f.write(b"not a pdf")
        f.close()  # Close so it can be opened by the service on Windows
        with pytest.raises(UnsupportedFileTypeError):
            extract_text_from_pdf(f.name)
    finally:
        if os.path.exists(f.name):
            os.unlink(f.name)
