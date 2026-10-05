"""Request middleware: trace id propagation + security headers.

Pure ASGI (not BaseHTTPMiddleware): contextvars set here are reliably visible
to route handlers and exception handlers downstream.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from project_backend.platform.observability.trace import (
    reset_trace_id,
    resolve_trace_id,
    set_trace_id,
)

Scope = dict
Message = dict
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


class TraceIdMiddleware:
    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict((k.decode().lower(), v.decode()) for k, v in scope["headers"])
        trace_id = resolve_trace_id(headers)
        token = set_trace_id(trace_id)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                raw = [(k, v) for k, v in message.get("headers", [])]
                raw.append((b"x-trace-id", trace_id.encode()))
                raw.append((b"x-content-type-options", b"nosniff"))
                # HSTS: only when the client used HTTPS (direct or via
                # x-forwarded-proto from a TLS-terminating proxy).
                proto = headers.get("x-forwarded-proto", scope.get("scheme", ""))
                if proto == "https":
                    raw.append(
                        (
                            b"strict-transport-security",
                            b"max-age=63072000; includeSubDomains",
                        )
                    )
                message["headers"] = raw
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            reset_trace_id(token)
