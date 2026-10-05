"""Request trace id propagation via contextvar (blueprint 04 §7).

Single source of truth for the trace id within one request:
- middleware validates the inbound `x-trace-id` / W3C `traceparent` (or
  generates one) and sets it here
- problem responses read it here → header and body carry the SAME value
- the logging filter reads it here → logs carry the real trace id

Client-provided ids are accepted only if they match TRACE_ID_PATTERN;
anything else (empty, too long, weird chars) is replaced by a fresh uuid hex.
This prevents log injection / header smuggling via the trace header.
"""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar, Token

TRACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# W3C traceparent: version-trace_id-parent_id-flags
# e.g. 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
TRACEPARENT_RE = re.compile(r"^[0-9a-f]{2}-([0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}$")

_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def normalize_trace_id(raw: str | None) -> str:
    """Validate a client-provided trace id; generate one when invalid."""
    if raw and TRACE_ID_PATTERN.fullmatch(raw):
        return raw
    return uuid.uuid4().hex


def trace_id_from_traceparent(traceparent: str | None) -> str | None:
    """Extract the 32-hex trace id from a W3C traceparent header.

    Returns None if the header is missing or malformed. The all-zero
    trace id (invalid per W3C) is rejected.
    """
    if not traceparent:
        return None
    m = TRACEPARENT_RE.fullmatch(traceparent.strip())
    if not m:
        return None
    trace_id = m.group(1)
    if trace_id == "0" * 32:
        return None
    return trace_id


def resolve_trace_id(headers: dict[str, str]) -> str:
    """Pick the trace id for a request.

    Priority: W3C traceparent > x-trace-id > generated.
    """
    from_traceparent = trace_id_from_traceparent(headers.get("traceparent"))
    if from_traceparent:
        return from_traceparent
    return normalize_trace_id(headers.get("x-trace-id"))


def set_trace_id(trace_id: str) -> Token[str]:
    return _trace_id_var.set(trace_id)


def get_trace_id() -> str:
    trace_id = _trace_id_var.get()
    if not trace_id:
        # Outside a request (e.g. worker, CLI): generate a fresh one so
        # callers never get an empty id.
        trace_id = uuid.uuid4().hex
        _trace_id_var.set(trace_id)
    return trace_id


def reset_trace_id(token: Token[str]) -> None:
    _trace_id_var.reset(token)
