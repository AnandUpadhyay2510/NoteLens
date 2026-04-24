"""
LLM client service tests.

Tests prompt sending, error handling, retry logic, and response validation
with mocked OpenAI API calls.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.llm_client import send_prompt
from app.utils.exceptions import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMResponseError,
)


def _make_mock_response(content: str = "Test response"):
    """Create a mock OpenAI ChatCompletion response."""
    mock_choice = MagicMock()
    mock_choice.message.content = content

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = MagicMock()
    return mock_response


# ---------------------------------------------------------------------------
# Success tests
# ---------------------------------------------------------------------------

@patch("app.services.llm_client._get_client")
def test_send_prompt_success(mock_get_client):
    """Test successful prompt returns response content."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response("Hello!")
    mock_get_client.return_value = mock_client

    result = send_prompt("Say hello")
    assert result == "Hello!"


@patch("app.services.llm_client._get_client")
def test_send_prompt_strips_whitespace(mock_get_client):
    """Test response content is stripped."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response("  spaced  ")
    mock_get_client.return_value = mock_client

    result = send_prompt("Test")
    assert result == "spaced"


# ---------------------------------------------------------------------------
# Error handling tests (PRD §6.4)
# ---------------------------------------------------------------------------

@patch("app.services.llm_client._get_client")
def test_send_prompt_auth_error(mock_get_client):
    """Test authentication error raises LLMAuthenticationError."""
    from openai import AuthenticationError

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_client.chat.completions.create.side_effect = AuthenticationError(
        message="Invalid key", response=mock_response, body=None
    )
    mock_get_client.return_value = mock_client

    with pytest.raises(LLMAuthenticationError):
        send_prompt("Test")


@patch("app.services.llm_client._get_client")
@patch("app.services.llm_client.time.sleep")  # Skip actual sleep in tests
def test_send_prompt_rate_limit_exhausted(mock_sleep, mock_get_client):
    """Test rate limit exhaustion after 3 retries raises LLMRateLimitError."""
    from openai import RateLimitError

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_client.chat.completions.create.side_effect = RateLimitError(
        message="Rate limited", response=mock_response, body=None
    )
    mock_get_client.return_value = mock_client

    with pytest.raises(LLMRateLimitError):
        send_prompt("Test")

    # Should have retried 3 times
    assert mock_client.chat.completions.create.call_count == 3


@patch("app.services.llm_client._get_client")
def test_send_prompt_empty_response(mock_get_client):
    """Test empty response raises LLMResponseError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response("")
    mock_get_client.return_value = mock_client

    with pytest.raises(LLMResponseError):
        send_prompt("Test")


@patch("app.services.llm_client._get_client")
def test_send_prompt_no_choices(mock_get_client):
    """Test response with no choices raises LLMResponseError."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = []
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    with pytest.raises(LLMResponseError):
        send_prompt("Test")


# ---------------------------------------------------------------------------
# Retry behavior tests
# ---------------------------------------------------------------------------

@patch("app.services.llm_client._get_client")
@patch("app.services.llm_client.time.sleep")
def test_send_prompt_rate_limit_then_success(mock_sleep, mock_get_client):
    """Test successful recovery after rate limit on first attempt."""
    from openai import RateLimitError

    mock_client = MagicMock()
    mock_response_429 = MagicMock()
    mock_response_429.status_code = 429

    # First call rate limited, second succeeds
    mock_client.chat.completions.create.side_effect = [
        RateLimitError(message="Rate limited", response=mock_response_429, body=None),
        _make_mock_response("Recovered!"),
    ]
    mock_get_client.return_value = mock_client

    result = send_prompt("Test")
    assert result == "Recovered!"
    assert mock_client.chat.completions.create.call_count == 2
