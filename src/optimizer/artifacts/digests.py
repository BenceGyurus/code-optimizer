from typing import Any


def make_digest(value: Any, limit: int = 1200) -> str:
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]"
