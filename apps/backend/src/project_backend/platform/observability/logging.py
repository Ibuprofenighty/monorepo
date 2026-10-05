"""Structured JSON logging. No PII / full bodies as default fields (blueprint 04 §7).

Stdlib only — no new dependencies. Every record carries trace_id from the
request context (Batch A), so logs join with problem responses on trace_id.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

from project_backend.platform.observability.trace import get_trace_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "trace_id": get_trace_id(),
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            payload["exc"] = self.formatException(record.exc_info)
        # Allow structured extras: log.info("...", extra={"user_id": ...})
        # (never put PII / secrets here — see module docstring)
        for key in ("extra_fields",):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def install_trace_filter() -> None:
    """No-op (Batch C): JsonFormatter reads trace_id directly.

    Kept for backward compatibility with code that calls it.
    """
    return None
