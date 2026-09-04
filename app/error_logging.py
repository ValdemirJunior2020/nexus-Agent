from __future__ import annotations

import json
import logging
import os
import re
import traceback
import uuid
import zipfile
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .config import ROOT

LOG_DIR = ROOT / "data" / "logs"
MAIN_LOG = LOG_DIR / "nexus.log"
ISSUES_LOG = LOG_DIR / "issues.jsonl"
FRIENDLY_ISSUE_MESSAGE = "I'm saving all the issues happening with me so Junior can fix it later."

_SENSITIVE = re.compile(r"(password|passwd|secret|token|authorization|cookie|api[_-]?key|pin)", re.I)
_CONFIGURED = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_value(value: Any, max_len: int = 1200) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value if len(value) <= max_len else value[:max_len] + "…"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            out[key_text] = "[REDACTED]" if _SENSITIVE.search(key_text) else _safe_value(item, max_len=max_len)
        return out
    if isinstance(value, (list, tuple, set)):
        return [_safe_value(x, max_len=max_len) for x in list(value)[:50]]
    return _safe_value(str(value), max_len=max_len)


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid adding duplicate handlers if uvicorn reloads the module.
    target = str(MAIN_LOG.resolve())
    for handler in root_logger.handlers:
        if isinstance(handler, RotatingFileHandler) and getattr(handler, "baseFilename", None) == target:
            _CONFIGURED = True
            return

    handler = RotatingFileHandler(
        MAIN_LOG,
        maxBytes=5 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    root_logger.addHandler(handler)
    _CONFIGURED = True
    logging.getLogger("nexus").info("NEXUS file logging initialized at %s", MAIN_LOG)


def record_issue(
    component: str,
    exc: BaseException | None = None,
    *,
    message: str | None = None,
    context: dict[str, Any] | None = None,
    severity: str = "error",
) -> str:
    """Persist one issue and return a short incident ID.

    The log intentionally stores operational metadata rather than full ticket/prompt text.
    """
    setup_logging()
    incident_id = "NX-" + uuid.uuid4().hex[:10].upper()
    err_text = message or (str(exc) if exc else "Unknown issue")
    record = {
        "incident_id": incident_id,
        "timestamp_utc": _utc_now(),
        "severity": severity,
        "component": component,
        "exception_type": type(exc).__name__ if exc else None,
        "error": _safe_value(err_text),
        "context": _safe_value(context or {}),
        "traceback": traceback.format_exc() if exc and exc.__traceback__ else None,
        "resolved": False,
    }
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with ISSUES_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger = logging.getLogger("nexus.issue")
    log_fn = logger.error if severity.lower() in {"error", "critical"} else logger.warning
    log_fn("%s | %s | %s", incident_id, component, err_text, exc_info=exc if exc else None)
    return incident_id


def friendly_issue_text(incident_id: str | None = None) -> str:
    if incident_id:
        return f"{FRIENDLY_ISSUE_MESSAGE} Issue ID: {incident_id}"
    return FRIENDLY_ISSUE_MESSAGE


def issue_count() -> int:
    if not ISSUES_LOG.exists():
        return 0
    with ISSUES_LOG.open("r", encoding="utf-8", errors="replace") as fh:
        return sum(1 for line in fh if line.strip())


def export_logs(destination: Path | None = None) -> Path:
    setup_logging()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = destination or (ROOT / f"NEXUS_ERROR_REPORT_{stamp}.zip")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if LOG_DIR.exists():
            for path in sorted(LOG_DIR.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=str(Path("logs") / path.relative_to(LOG_DIR)))
        summary = (
            f"NEXUS Error Report\n"
            f"Created: {_utc_now()}\n"
            f"Issue count: {issue_count()}\n"
            f"Friendly message: {FRIENDLY_ISSUE_MESSAGE}\n"
        )
        zf.writestr("README.txt", summary)
    return destination
