"""
LLM client service.

Implements PRD §4.2 — OpenRouter API Integration. Wraps all LLM API calls
using the OpenAI-compatible Python SDK with retry logic and error handling.
"""

import time
from typing import Any

import structlog
from openai import APIConnectionError, APIError, AuthenticationError, OpenAI, RateLimitError

from app.config import get_settings
from app.utils.exceptions import LLMAuthenticationError, LLMRateLimitError, LLMResponseError

logger = structlog.get_logger(__name__)
settings = get_settings()

MAX_RETRIES = 3
BASE_RETRY_DELAY = 2.0


def _get_client() -> OpenAI:
    """Create OpenAI client configured for OpenRouter (PRD §4.2)."""
    if not settings.OPENROUTER_API_KEY:
        raise LLMAuthenticationError()
    return OpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )


def send_prompt(
    user_prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int | None = None,
) -> str:
    """
    Send a prompt to the LLM via OpenRouter and return the response.

    Implements retry with exponential backoff for rate limits (PRD §6.4).

    Args:
        user_prompt: The main prompt text.
        system_prompt: System-level instructions for the LLM.
        model: LLM model identifier. Falls back to DEFAULT_MODEL.
        temperature: Sampling temperature (0.0–2.0).
        max_tokens: Maximum tokens in the response.

    Returns:
        The LLM-generated response text.

    Raises:
        LLMAuthenticationError: If the API key is invalid.
        LLMRateLimitError: If rate limit exceeded after retries.
        LLMResponseError: If the response is empty or malformed.
    """
    client = _get_client()
    model = model or settings.DEFAULT_MODEL
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    logger.info("llm_request_started", model=model, prompt_length=len(user_prompt))

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            params: dict[str, Any] = {
                "model": model, "messages": messages, "temperature": temperature,
            }
            if max_tokens:
                params["max_tokens"] = max_tokens

            start = time.time()
            response = client.chat.completions.create(**params)
            elapsed = time.time() - start

            if not response.choices:
                raise LLMResponseError("Response contained no choices.")

            content = response.choices[0].message.content
            if not content or not content.strip():
                raise LLMResponseError("Response content was empty.")

            logger.info("llm_request_completed", model=model, elapsed=round(elapsed, 2))
            return content.strip()

        except AuthenticationError as e:
            raise LLMAuthenticationError() from e
        except RateLimitError as e:
            delay = BASE_RETRY_DELAY * (2 ** (attempt - 1))
            logger.warning("llm_rate_limit", attempt=attempt, delay=delay)
            if attempt < MAX_RETRIES:
                time.sleep(delay)
            else:
                raise LLMRateLimitError() from e
        except (APIConnectionError, APIError) as e:
            delay = BASE_RETRY_DELAY * (2 ** (attempt - 1))
            logger.warning("llm_api_error", attempt=attempt, error=str(e))
            if attempt < MAX_RETRIES:
                time.sleep(delay)
            else:
                raise LLMResponseError(f"API error after {MAX_RETRIES} attempts: {e}") from e
        except (LLMResponseError, LLMAuthenticationError, LLMRateLimitError):
            raise
        except Exception as e:
            raise LLMResponseError(f"Unexpected error: {e}") from e

    raise LLMResponseError("Request failed after all retries.")
