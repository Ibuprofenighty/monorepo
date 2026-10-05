"""Public error → RFC 9457 problem+json. Reads the GENERATED registry.

platform never imports business modules (blueprint 03 §1): modules convert their
domain errors to MappedError in presentation/http/error_mapping.py; this handler
only knows public codes.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from project_backend.generated.http.errors import ERROR_HTTP_STATUS, ERROR_TITLES, ERROR_TYPES
from project_backend.platform.observability.trace import get_trace_id

log = logging.getLogger(__name__)
PROBLEM_JSON = "application/problem+json"


class MappedError(Exception):
    """A public, contract-defined failure. Modules raise this via their error_mapping."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        if code not in ERROR_HTTP_STATUS:
            raise ValueError(f"unknown public error code: {code}")
        self.code = code
        self.detail = detail


def problem_response(
    code: str, detail: str = "", instance: str = "", headers: dict[str, str] | None = None
) -> JSONResponse:
    status = ERROR_HTTP_STATUS[code]
    body: dict[str, object] = {
        "type": ERROR_TYPES[code],
        # RFC 9457: title is human-readable. The stable machine contract is `code`.
        "title": ERROR_TITLES[code],
        "status": status,
        "code": code,
        "trace_id": get_trace_id(),
    }
    if detail:
        body["detail"] = detail
    if instance:
        body["instance"] = instance
    response_headers = dict(headers or {})
    if status == 401 and "www-authenticate" not in {k.lower() for k in response_headers}:
        # RFC 6750 §3: Bearer 401 MUST carry a WWW-Authenticate challenge.
        # The registry (AUTHN.*) requires the challenge header per scheme.
        challenge = "Bearer"
        if code == "AUTHN.INVALID":
            challenge += ', error="invalid_token"'
        response_headers["WWW-Authenticate"] = challenge
    return JSONResponse(
        status_code=status, content=body, media_type=PROBLEM_JSON, headers=response_headers
    )


async def _mapped_error_handler(request: Request, exc: MappedError) -> JSONResponse:
    return problem_response(exc.code, exc.detail, instance=str(request.url.path))


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never leak tracebacks/SQL/PII. Diagnose via trace_id in controlled logs.
    trace_id = get_trace_id()
    log.exception("unhandled error trace_id=%s path=%s", trace_id, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "type": ERROR_TYPES["INTERNAL"],
            "title": ERROR_TITLES["INTERNAL"],
            "status": 500,
            "code": "INTERNAL",
            "trace_id": trace_id,
        },
        media_type=PROBLEM_JSON,
    )


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # 422 with the contract's Problem shape — never FastAPI's default body (blueprint 03 §5).
    detail = "; ".join(
        f"{'.'.join(str(p) for p in e['loc'] if p != 'body')}: {e['msg']}" for e in exc.errors()
    )
    return problem_response("VALIDATION.FAILED", detail, instance=str(request.url.path))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(MappedError, _mapped_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_handler)
