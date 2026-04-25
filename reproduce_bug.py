from app.services.syllabus_filter import run_filter
import pytest
from unittest.mock import patch

def test_reproduce_format_error():
    syllabus_text = "Syllabus with curly braces {broken}"
    notes_text = "Some notes"

    try:
        # We don't even need to mock LLM if it fails during formatting before LLM call
        run_filter(syllabus_text, notes_text)
    except KeyError as e:
        print(f"\nCaught expected KeyError: {e}")
    except Exception as e:
        print(f"\nCaught exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_reproduce_format_error()
