"""
app/utils/logging.py - Structured JSON logging.

log_event() emits machine-readable JSON log lines that include request_id,
stage, event name, and any extra keyword arguments (duration_ms, metrics, etc.)
"""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional


class _JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # If the record carries structured extras, include them
        for key in ("request_id", "stage", "event"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Call once at application startup."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def log_event(
    logger_instance: logging.Logger,
    request_id: str,
    stage: str,
    event: str,
    level: int = logging.INFO,
    **kwargs: Any,
) -> None:
    """
    Emit a structured pipeline event log line.

    All keyword arguments are included as top-level fields in the JSON output,
    enabling easy grep / jq filtering by request_id, stage, or event.
    """
    extra = {"request_id": request_id, "stage": stage, "event": event}
    msg = json.dumps({"request_id": request_id, "stage": stage, "event": event, **kwargs}, default=str)
    logger_instance.log(level, msg, extra=extra)
