"""Batch C: JSON logs, /ready, W3C traceparent."""

from __future__ import annotations

import json
import logging

from httpx import ASGITransport, AsyncClient
from project_backend.bootstrap.app import create_app
from project_backend.platform.config.settings import Settings
from project_backend.platform.observability import logging as log_module
from project_backend.platform.observability.trace import (
    resolve_trace_id,
    trace_id_from_traceparent,
)


def _app(**kw):
    return create_app(Settings(_env_file=None, **kw))


async def _get(app, path, headers=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path, headers=headers or {})


def test_json_log_format(capsys):
    log_module.setup_logging("INFO")
    logger = logging.getLogger("test.json")
    logger.info("hello world")
    out = capsys.readouterr().out.strip()
    record = json.loads(out)
    assert record["level"] == "INFO"
    assert record["logger"] == "test.json"
    assert record["msg"] == "hello world"
    assert "trace_id" in record
    assert "ts" in record


def test_traceparent_valid():
    tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    assert trace_id_from_traceparent(tp) == "4bf92f3577b34da6a3ce929d0e0e4736"


def test_traceparent_invalid():
    assert trace_id_from_traceparent(None) is None
    assert trace_id_from_traceparent("bogus") is None
    # all-zero trace id is invalid per W3C
    assert trace_id_from_traceparent("00-" + "0" * 32 + "-00f067aa0ba902b7-01") is None


def test_resolve_prefers_traceparent():
    headers = {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "x-trace-id": "client-id",
    }
    assert resolve_trace_id(headers) == "4bf92f3577b34da6a3ce929d0e0e4736"


async def test_traceparent_propagated_to_response():
    tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    r = await _get(_app(), "/api/v1/resources", {"traceparent": tp})
    assert r.status_code == 401
    assert r.headers["x-trace-id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert r.json()["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"


async def test_ready_reports_db_and_redis():
    # No real DB/Redis here: readiness must report 503, not crash.
    r = await _get(_app(), "/api/v1/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "not_ready"
    assert "database" in body["checks"]
    # begin capability:redis
    assert "redis" in body["checks"]
    # end capability:redis


async def test_health_still_ok():
    r = await _get(_app(), "/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
