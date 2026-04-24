# Product Requirements Document (PRD)

**Product Name:** GPT Wrapper with Syllabus Filter
**Document Version:** 1.0
**Author:** Manus AI
**Date:** April 23, 2026
**Status:** Draft

---

## 1. Executive Summary

This document specifies the product requirements for a Python-based GPT wrapper application that integrates with the OpenRouter API to process multi-modal inputs — text, audio, and PDF. The application's flagship capability is the **Syllabus Filter**, an intelligent academic study assistant that cross-references student notes against a course syllabus and produces a clean, relevant subset of the notes aligned strictly with the syllabus topics. The goal is to reduce study overhead for students and ensure that course preparation remains tightly scoped to the required curriculum.

---

## 2. Problem Statement

Students frequently accumulate lecture notes, supplementary readings, and personal annotations that span far beyond the scope of their official course syllabus. During exam preparation, identifying which portions of their notes are actually examinable is a time-consuming and error-prone process. Existing tools either require manual review or lack the contextual intelligence to distinguish between in-scope and out-of-scope content. This application solves that problem by automating the cross-referencing pipeline using a large language model.

---

## 3. Target Audience

The primary users of this application are students at the undergraduate and postgraduate level who need to filter and organize their study materials. Secondary users include educators and tutors who wish to align student-submitted notes with official course syllabi. A tertiary audience includes researchers and knowledge workers who require automated document cross-referencing for structured information extraction.

---

## 4. Core Features

### 4.1 Multi-Modal Input Processing

The application must accept three distinct input modalities and convert each into plain text before any LLM interaction occurs. This preprocessing layer ensures that the OpenRouter API always receives clean, structured text regardless of the original input format.

| Input Type | Accepted Formats | Preprocessing Method |
|---|---|---|
| Text | Plain string | None required; passed directly |
| Audio | `.mp3`, `.wav`, `.m4a`, `.ogg` | Transcribed via OpenAI Whisper or equivalent |
| PDF | `.pdf` | Text extracted via PyMuPDF (`fitz`) or `pdfplumber` |

All preprocessing must be handled within a dedicated `input_handler` module. If a file format is not supported, the application must raise a descriptive error and halt processing gracefully rather than passing malformed input to the LLM.

### 4.2 OpenRouter API Integration

The application integrates with the OpenRouter API using the standard OpenAI-compatible Python SDK. The base URL is configured to `https://openrouter.ai/api/v1`, and authentication is handled via the `OPENROUTER_API_KEY` environment variable loaded through `python-dotenv`. The default model should be a high-capability model such as `anthropic/claude-3.5-sonnet` or `openai/gpt-4o`, with the option to override this via configuration.

All API calls must be encapsulated within a dedicated `llm_client` module that handles request formatting, response parsing, retry logic, and error reporting. This abstraction ensures that the rest of the application remains decoupled from the specifics of the API integration.

### 4.3 Syllabus Filter (Flagship Feature)

The Syllabus Filter is the core differentiator of this application. It accepts two PDF inputs — a **Syllabus PDF** and a **Notes PDF** — and produces a filtered, cleaned version of the notes that retains only content relevant to the syllabus. The feature operates as a two-stage LLM pipeline:

**Stage 1 — Syllabus Parsing:** The extracted syllabus text is sent to the LLM with a prompt that instructs it to act as an academic study assistant and identify all core topics, subtopics, learning objectives, and key concepts covered in the course.

**Stage 2 — Notes Filtering:** The extracted notes text, along with the list of identified syllabus topics from Stage 1, is sent to the LLM. The model is instructed to methodically review the notes section by section, retaining content that is directly relevant to the syllabus topics and removing content that is off-topic, tangential, or not covered by the curriculum.

The output of the Syllabus Filter is a plain text document consisting of a brief header listing the identified syllabus topics, followed by the filtered notes with their original logical flow and structure preserved as closely as possible.

---

## 5. Technical Architecture

### 5.1 Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| LLM API | OpenRouter via OpenAI Python SDK |
| PDF Extraction | PyMuPDF (`fitz`) or `pdfplumber` |
| Audio Transcription | OpenAI Whisper API or local Whisper model |
| Environment Management | `python-dotenv` |
| Dependency Management | `pip` with `requirements.txt` |

### 5.2 Module Structure

The codebase must be organized into clearly separated modules, each with a single, well-defined responsibility. The following table describes the required modules and their roles:

| Module | Responsibility |
|---|---|
| `main.py` | Application entry point; orchestrates the overall flow and routes inputs to the appropriate handlers |
| `input_handler.py` | Handles text passthrough, audio transcription, and PDF text extraction |
| `llm_client.py` | Wraps all OpenRouter API calls; manages authentication, request construction, response parsing, and retries |
| `syllabus_filter.py` | Implements the two-stage Syllabus Filter pipeline, including specialized prompt construction |
| `utils.py` | Provides shared helper functions for file validation, error logging, and environment configuration |

### 5.3 Data Flow

The following describes the end-to-end data flow for the Syllabus Filter use case:

1. The user provides a Syllabus PDF and a Notes PDF as inputs.
2. `input_handler.py` extracts raw text from both files using PyMuPDF or pdfplumber.
3. `syllabus_filter.py` constructs a Stage 1 prompt and calls `llm_client.py` to extract syllabus topics from the syllabus text.
4. `syllabus_filter.py` constructs a Stage 2 prompt using the extracted topics and the notes text, then calls `llm_client.py` again to perform the filtering.
5. The filtered notes are returned as plain text output, prefixed with the identified syllabus topics header.

---

## 6. Functional Requirements

### 6.1 Input Handling

The application must validate all uploaded files before processing. Unsupported file types must be rejected with a clear, user-facing error message. For audio files, the transcription step must complete successfully before the transcript is passed downstream; any transcription failure must be surfaced as a distinct error. For PDF files, if the extraction yields an empty string (which may occur with scanned image-based PDFs lacking embedded text), the application must notify the user and suggest enabling OCR as a future option rather than silently passing empty content to the LLM.

### 6.2 LLM Prompt Design for Syllabus Filter

The prompts used in the Syllabus Filter pipeline are critical to the quality of the output. The Stage 1 prompt must explicitly instruct the model to extract a structured list of topics and learning objectives from the syllabus text. The Stage 2 prompt must frame the model as an academic study assistant, provide the topic list from Stage 1, and instruct the model to evaluate each section of the notes for relevance before producing the filtered output. Both prompts must include clear instructions to preserve the original structure and logical flow of the notes where content is retained.

### 6.3 Output Format

All outputs from the application must be returned as plain text. For the Syllabus Filter feature specifically, the output must begin with a structured header in the following format:

```
=== IDENTIFIED SYLLABUS TOPICS ===
[List of topics extracted from the syllabus]

=== FILTERED NOTES ===
[Filtered notes content]
```

### 6.4 Error Handling Requirements

Robust error handling is mandatory throughout the application. The table below summarizes the key error scenarios and the expected handling behavior:

| Error Scenario | Expected Behavior |
|---|---|
| Unsupported file type uploaded | Raise a `ValueError` with a descriptive message; do not proceed |
| PDF extraction yields empty text | Notify the user; suggest OCR support; halt the pipeline |
| Audio transcription fails | Surface the transcription error; do not pass empty text to LLM |
| OpenRouter API authentication error | Log the error; display a clear message about the invalid API key |
| OpenRouter API rate limit exceeded | Implement exponential backoff with a maximum of 3 retries |
| LLM returns empty or malformed response | Log the raw response; return a user-facing error message |
| Both syllabus and notes not provided for filter | Validate inputs upfront; raise an error before any API call is made |

---

## 7. Non-Functional Requirements

**Performance:** The application should complete a typical Syllabus Filter operation (two LLM API calls with moderate-length documents) within a reasonable time frame. PDF extraction and audio transcription should complete locally or via API within acceptable latency bounds.

**Security:** The `OPENROUTER_API_KEY` must never be hardcoded in the source code. All sensitive configuration must be managed via `.env` files, which must be listed in `.gitignore` to prevent accidental exposure in version control.

**Maintainability:** The modular architecture described in Section 5.2 must be strictly followed. Each module must include a module-level docstring, and all public functions must include docstrings with parameter and return type descriptions. Inline comments must be used to explain non-obvious logic, particularly within `syllabus_filter.py`.

**Portability:** The application must run on any system with Python 3.10+ installed. All dependencies must be listed in a `requirements.txt` file with pinned version numbers to ensure reproducible environments.

---

## 8. Acceptance Criteria

The following criteria must be met for the application to be considered complete and ready for use:

| Criterion | Verification Method |
|---|---|
| Text input is passed to the LLM and a response is returned | Manual test with a sample text prompt |
| Audio file is correctly transcribed and the transcript is sent to the LLM | Upload a sample `.mp3` and verify the transcript |
| PDF file text is correctly extracted and sent to the LLM | Upload a sample PDF and verify the extracted content |
| Syllabus Filter correctly identifies topics from a sample syllabus | Compare LLM output against known syllabus topics |
| Syllabus Filter correctly removes off-topic content from notes | Manually verify filtered output against source notes |
| Unsupported file types are rejected with a clear error | Attempt to upload a `.docx` file and verify the error |
| API key is loaded from environment variable, not hardcoded | Code review of `llm_client.py` and `.env` configuration |
| All modules have docstrings and inline comments on key logic | Code review |

---

## 9. Out of Scope (Version 1.0)

The following capabilities are explicitly excluded from the Version 1.0 scope and are candidates for future releases:

**OCR Support:** Handling scanned PDFs that do not contain embedded text requires integration with an OCR engine such as Tesseract. This is deferred to a future version.

**Web Interface:** A graphical user interface built with Streamlit, Gradio, or a web framework is not included in Version 1.0. The application will be operated via command-line or programmatic invocation.

**Export Options:** The ability to download filtered notes as a PDF or Markdown file is a future enhancement. Version 1.0 outputs plain text only.

**Multi-Language Support:** Handling syllabi and notes in languages other than English is not a Version 1.0 requirement.

---

## 10. Dependencies & Environment Setup

The following packages must be listed in `requirements.txt`:

| Package | Purpose |
|---|---|
| `openai` | OpenAI-compatible SDK for OpenRouter API calls |
| `python-dotenv` | Loading environment variables from `.env` files |
| `PyMuPDF` (`fitz`) | PDF text extraction |
| `pdfplumber` | Alternative PDF text extraction library |
| `openai-whisper` | Local audio transcription (or use OpenAI Whisper API) |

The `.env` file must contain at minimum:

```
OPENROUTER_API_KEY=your_api_key_here
DEFAULT_MODEL=anthropic/claude-3.5-sonnet
```

---

*End of Document*
