import sys
import os

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.syllabus_filter import (
    STAGE_1_USER_PROMPT_TEMPLATE,
    STAGE_2_SYSTEM_PROMPT,
    STAGE_2_USER_PROMPT_TEMPLATE
)

def test_format_bug():
    print("Testing Stage 1 User Prompt Template...")
    try:
        res = STAGE_1_USER_PROMPT_TEMPLATE.format(syllabus_text="Syllabus with {braces}")
        print(f"Result: {res}")
    except KeyError as e:
        print(f"FAILED: Stage 1 User Prompt Template failed with KeyError: {e}")

    print("\nTesting Stage 2 System Prompt Template...")
    try:
        res = STAGE_2_SYSTEM_PROMPT.format(topics="Topics with {braces}")
        print(f"Result: {res}")
    except KeyError as e:
        print(f"FAILED: Stage 2 System Prompt Template failed with KeyError: {e}")

    print("\nTesting Stage 2 User Prompt Template...")
    try:
        res = STAGE_2_USER_PROMPT_TEMPLATE.format(notes_text="Notes with {braces}")
        print(f"Result: {res}")
    except KeyError as e:
        print(f"FAILED: Stage 2 User Prompt Template failed with KeyError: {e}")

if __name__ == "__main__":
    test_format_bug()
