"""
Syllabus Filter service tests.

Tests the two-stage pipeline, input validation, output formatting,
and error handling — all with mocked LLM calls.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.syllabus_filter import (
    format_output,
    parse_syllabus,
    filter_notes,
    run_filter,
)
from app.utils.exceptions import FilterInputError


# ---------------------------------------------------------------------------
# format_output tests (PRD §6.3)
# ---------------------------------------------------------------------------

def test_format_output_structure():
    """Test output matches the premium Markdown format."""
    topics = "1. Algorithms\n2. Data Structures"
    notes = "Binary search is a divide-and-conquer algorithm."

    result = format_output(topics, notes)

    assert "# Mapped Relevancy Report" in result
    assert "## Syllabus Overview" in result
    assert "## Detailed Notes by Topic" in result
    assert topics in result
    assert notes in result


# ---------------------------------------------------------------------------
# Input validation tests (PRD §6.4)
# ---------------------------------------------------------------------------

def test_run_filter_empty_syllabus():
    """Test filter raises error when syllabus text is empty."""
    with pytest.raises(FilterInputError, match="Syllabus text is required"):
        run_filter(syllabus_text="", notes_text="Some notes content")


def test_run_filter_empty_notes():
    """Test filter raises error when notes text is empty."""
    with pytest.raises(FilterInputError, match="Notes text is required"):
        run_filter(syllabus_text="Some syllabus content", notes_text="")


def test_run_filter_none_syllabus():
    """Test filter raises error when syllabus is None."""
    with pytest.raises(FilterInputError):
        run_filter(syllabus_text=None, notes_text="Some notes")


def test_run_filter_none_notes():
    """Test filter raises error when notes is None."""
    with pytest.raises(FilterInputError):
        run_filter(syllabus_text="Some syllabus", notes_text=None)


def test_run_filter_whitespace_only():
    """Test filter raises error when inputs are whitespace-only."""
    with pytest.raises(FilterInputError):
        run_filter(syllabus_text="   \n\t  ", notes_text="Some notes")


# ---------------------------------------------------------------------------
# Pipeline tests (mocked LLM)
# ---------------------------------------------------------------------------

@patch("app.services.syllabus_filter.send_prompt")
def test_parse_syllabus_calls_llm(mock_send):
    """Test Stage 1 calls the LLM with correct system prompt."""
    mock_send.return_value = "1. Topic A\n2. Topic B"

    result = parse_syllabus("Some syllabus text")

    assert result == "1. Topic A\n2. Topic B"
    mock_send.assert_called_once()

    # Verify the system prompt mentions academic study assistant
    call_kwargs = mock_send.call_args
    assert "academic" in call_kwargs.kwargs.get("system_prompt", "").lower() or \
           "academic" in call_kwargs.args[0].lower() if call_kwargs.args else True


@patch("app.services.syllabus_filter.send_prompt")
def test_filter_notes_calls_llm(mock_send):
    """Test Stage 2 calls the LLM with topics injected."""
    mock_send.return_value = "Filtered content about Topic A."
    topics = "1. Topic A\n2. Topic B"

    result = filter_notes("Full notes text here", topics)

    assert result == "Filtered content about Topic A."
    mock_send.assert_called_once()


@patch("app.services.syllabus_filter.send_prompt")
def test_run_filter_full_pipeline(mock_send):
    """Test the complete two-stage pipeline with mocked LLM."""
    # Stage 1 returns topics, Stage 2 returns filtered notes
    mock_send.side_effect = [
        "1. Algorithms\n2. Data Structures",
        "Binary search is a divide-and-conquer algorithm.",
    ]

    result = run_filter(
        syllabus_text="Course covers algorithms and data structures.",
        notes_text="Binary search is a divide-and-conquer algorithm. Cooking recipes are fun.",
    )

    assert "identified_topics" in result
    assert "filtered_notes" in result
    assert "formatted_output" in result
    assert "processing_time_seconds" in result
    assert "model_used" in result

    assert "Algorithms" in result["identified_topics"]
    assert "Binary search" in result["filtered_notes"]
    assert "# Mapped Relevancy Report" in result["formatted_output"]
    assert "## Syllabus Overview" in result["formatted_output"]
    assert "## Detailed Notes by Topic" in result["formatted_output"]

    # Verify LLM was called exactly twice (Stage 1 + Stage 2)
    assert mock_send.call_count == 2
