import re

_INJECTION_MARKERS = re.compile(
    r"(?i)(ignore (all )?previous|system prompt|you are now|### instruction)",
)


def sanitize_user_question(question: str) -> str:
    cleaned = question.strip()
    if _INJECTION_MARKERS.search(cleaned):
        return cleaned + "\n[Note: answer only from provided context.]"
    return cleaned
