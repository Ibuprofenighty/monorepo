"""Batch A: HTTP semantics — trace propagation, 401 challenge, problem titles, docs gating."""

from __future__ import annotations

import re

from httpx import ASGITransport, AsyncClient
from project_backend.bootstrap.app import create_app
from project_backend.platform.config.settings import Settings

TRACE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$|^([0-9a-f]{32})$")


def _app(**kw):
    settings = Settings(_env_file=None, **kw)
    return create_app(settings)


async def _get(app, path, headers=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path, headers=headers or {})


async def test_trace_id_header_matches_body():
    # 401 triggers a problem response; header and body must carry the same id.
    r = await _get(_app(), "/api/v1/resources")
    assert r.status_code == 401
    body = r.json()
    assert r.headers["x-trace-id"] == body["trace_id"]
    assert TRACE_RE.fullmatch(body["trace_id"])


async def test_trace_id_client_provided_valid_is_echoed():
    r = await _get(_app(), "/api/v1/resources", {"x-trace-id": "client-123_abc"})
    assert r.status_code == 401
    assert r.headers["x-trace-id"] == "client-123_abc"
    assert r.json()["trace_id"] == "client-123_abc"


async def test_trace_id_client_provided_invalid_is_replaced():
    r = await _get(_app(), "/api/v1/resources", {"x-trace-id": "evil\ninjected"})
    assert r.status_code == 401
    new_id = r.headers["x-trace-id"]
    assert new_id != "evil\ninjected"
    assert TRACE_RE.fullmatch(new_id)
    assert r.json()["trace_id"] == new_id


async def test_401_carries_www_authenticate():
    r = await _get(_app(), "/api/v1/resources")
    assert r.status_code == 401
    assert r.headers["www-authenticate"].startswith("Bearer")
    assert r.json()["code"] == "AUTHN.REQUIRED"


async def test_401_invalid_token_challenge():
    r = await _get(_app(), "/api/v1/resources", {"authorization": "Bearer bogus"})
    assert r.status_code == 401
    assert 'error="invalid_token"' in r.headers["www-authenticate"]
    assert r.json()["code"] == "AUTHN.INVALID"


async def test_problem_title_is_human_readable():
    r = await _get(_app(), "/api/v1/resources")
    body = r.json()
    assert body["code"] == "AUTHN.REQUIRED"  # machine contract stays
    assert body["title"] == "Authentication required"  # RFC 9457: human-readable
    assert body["title"] != body["code"]


async def test_docs_enabled_in_dev():
    app = _app(app_env="dev")
    r = await _get(app, "/docs")
    assert r.status_code == 200


async def test_docs_disabled_in_production():
    app = _app(app_env="production", jwt_secret="s" * 32)
    r = await _get(app, "/docs")
    assert r.status_code == 404
    r = await _get(app, "/redoc")
    assert r.status_code == 404
