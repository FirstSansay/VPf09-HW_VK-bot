from __future__ import annotations


def truncate(text: str, limit: int) -> str:
    """Обрезает текст до limit символов, не разрывая слова."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    idx = cut.rfind(" ")
    if idx > int(limit * 0.6):
        cut = cut[:idx]
    return cut.rstrip(" .,;:!?") + "…"


def normalize_text(text: str | None) -> str:
    return (text or "").strip().replace("\r\n", "\n")