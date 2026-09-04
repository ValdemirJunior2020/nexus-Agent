import re
from typing import Any

from .config import CONFIG
from .memory import teach_memory

_EXPLICIT_PATTERNS = [
    r"^remember(?: this)?[:\s-]+(.+)$",
    r"^learn(?: this)?[:\s-]+(.+)$",
    r"^correction[:\s-]+(.+)$",
    r"^from now on[,\s:]+(.+)$",
    r"^my preference is[:\s-]+(.+)$",
]


def extract_explicit_teaching(text: str) -> str | None:
    value = (text or "").strip()
    for pattern in _EXPLICIT_PATTERNS:
        m = re.match(pattern, value, flags=re.I | re.S)
        if m:
            lesson = m.group(1).strip()
            return lesson if len(lesson) >= 4 else None
    # "when I say X, do Y" is a common durable correction/preference.
    if re.search(r"\bwhen i (?:say|ask|mention)\b", value, flags=re.I) and len(value) < 1200:
        return value
    return None


def auto_capture_explicit_teaching(user_id: str, text: str, session_id: str = "default") -> dict[str, Any] | None:
    cfg = CONFIG.get("learning", {})
    if not cfg.get("enabled", True) or not cfg.get("auto_capture_explicit_teaching", True):
        return None
    lesson = extract_explicit_teaching(text)
    if not lesson:
        return None
    memory_id = teach_memory(
        user_id=user_id or "default",
        content=lesson,
        kind="correction",
        scope="user",
        source=f"explicit-teaching:{session_id}",
        confidence=1.0,
    )
    return {"saved": True, "memory_id": memory_id, "memory": lesson}
