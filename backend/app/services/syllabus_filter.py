"""
Syllabus Filter service.

Implements PRD §4.3 — the flagship two-stage LLM pipeline that accepts
a syllabus and notes, extracts topics from the syllabus (Stage 1), then
filters the notes to retain only syllabus-relevant content (Stage 2).

Output follows the format specified in PRD §6.3.
"""

import time

import structlog

from app.services.llm_client import send_prompt
from app.utils.exceptions import FilterInputError

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates (PRD §6.2)
# ---------------------------------------------------------------------------

STAGE_1_SYSTEM_PROMPT = """You are a syllabus parser. 
Extract all topics and sub-topics exactly as they appear in the syllabus. 
- Use the original wording.
- Format as a Markdown list.
- DO NOT summarize or rephrase."""

STAGE_1_USER_PROMPT_TEMPLATE = """{syllabus_text}"""

STAGE_2_SYSTEM_PROMPT = """You are an inclusive academic filter and mapper.
Compare the syllabus topics provided below with the student notes. 
For each topic, extract the relevant content from the notes and place it directly under that topic heading.

Rules:
1. Be INCLUSIVE: Only omit notes if they are clearly unrelated (>80% irrelevant).
2. Structure the output as:
   ### [Syllabus Topic Name]
   [Relevant parts of the notes for this topic]
3. If multiple topics relate to the same note section, include it under both.
4. Preserve the original wording of the notes.
5. REMOVE college headers, dates, and logistical metadata.

=== SYLLABUS TOPICS ===
{topics}"""

STAGE_2_USER_PROMPT_TEMPLATE = """{notes_text}"""


# ---------------------------------------------------------------------------
# Pipeline functions
# ---------------------------------------------------------------------------

def parse_syllabus(syllabus_text: str, model: str | None = None) -> str:
    """
    Stage 1 — Extract structured topics from syllabus text.
    """
    logger.info("syllabus_parse_started", text_length=len(syllabus_text))

    user_prompt = STAGE_1_USER_PROMPT_TEMPLATE.format(syllabus_text=syllabus_text)

    topics = send_prompt(
        user_prompt=user_prompt,
        system_prompt=STAGE_1_SYSTEM_PROMPT,
        model=model,
        temperature=0.0,
    )

    logger.info("syllabus_parse_completed", topics_length=len(topics))
    return topics


def filter_notes(notes_text: str, topics: str, model: str | None = None) -> str:
    """
    Stage 2 — Filter notes for syllabus relevance.
    """
    logger.info("notes_filter_started", text_length=len(notes_text))

    system_prompt = STAGE_2_SYSTEM_PROMPT.format(topics=topics)
    user_prompt = STAGE_2_USER_PROMPT_TEMPLATE.format(notes_text=notes_text)

    filtered = send_prompt(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=0.0,
    )

    logger.info("notes_filter_completed", filtered_length=len(filtered))
    return filtered


def format_output(topics: str, filtered_notes: str) -> str:
    """
    Format the final output as a Markdown document.
    """
    return (
        f"# Mapped Relevancy Report\n\n"
        f"This report maps your course syllabus topics directly to relevant sections of your notes.\n\n"
        f"## Syllabus Overview\n"
        f"{topics}\n\n"
        f"---\n\n"
        f"## Detailed Notes by Topic\n"
        f"{filtered_notes}"
    )


def run_filter(
    syllabus_text: str,
    notes_text: str,
    model: str | None = None,
) -> dict:
    """
    Execute the complete two-stage Syllabus Filter pipeline.

    Orchestrates Stage 1 (syllabus parsing) and Stage 2 (notes filtering),
    validates inputs upfront (PRD §6.4), tracks processing time, and
    returns the formatted output.

    Args:
        syllabus_text: Plain text of the syllabus.
        notes_text: Plain text of the notes.
        model: Optional LLM model override.

    Returns:
        Dictionary with keys:
        - 'identified_topics': Stage 1 output
        - 'filtered_notes': Stage 2 output
        - 'formatted_output': Combined output per PRD §6.3
        - 'processing_time_seconds': Total processing time
        - 'model_used': The model used

    Raises:
        FilterInputError: If either input is missing or empty (PRD §6.4).
    """
    # Validate inputs upfront before any API call (PRD §6.4)
    if not syllabus_text or not syllabus_text.strip():
        raise FilterInputError("Syllabus text is required and cannot be empty.")
    if not notes_text or not notes_text.strip():
        raise FilterInputError("Notes text is required and cannot be empty.")

    from app.config import get_settings
    model = model or get_settings().DEFAULT_MODEL

    logger.info(
        "filter_pipeline_started",
        syllabus_length=len(syllabus_text),
        notes_length=len(notes_text),
        model=model,
    )

    start_time = time.time()

    # Stage 1: Parse syllabus topics
    topics = parse_syllabus(syllabus_text, model=model)

    # Stage 2: Filter notes against topics
    filtered = filter_notes(notes_text, topics, model=model)

    processing_time = round(time.time() - start_time, 2)

    # Format output per PRD §6.3
    formatted = format_output(topics, filtered)

    logger.info(
        "filter_pipeline_completed",
        processing_time=processing_time,
        topics_length=len(topics),
        filtered_length=len(filtered),
    )

    return {
        "identified_topics": topics,
        "filtered_notes": filtered,
        "formatted_output": formatted,
        "processing_time_seconds": processing_time,
        "model_used": model,
    }
