"""WeChat code2session adapter. HTTP is a fake transport; the adapter is real."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from project_backend.generated.http.errors import ErrorCode
from project_backend.platform.authn.verifiers.wechat import (
    DEV_WECHAT_APP_ID,
    DEV_WECHAT_APP_SECRET,
    Verifier,
    exchange_code,
    register_auth_routes,
    validate_identity_settings,
    verify_bearer_token,
)
from project_backend.platform.http.exception_handlers import MappedError
from pydantic import SecretStr

VERIFIER = Verifier(
    app_id="wx-test",
    app_secret="app-secret-value",
    secret="test-secret-0123456789abcdef0123456789",
    algorithm="HS256",
    issuer="test",
    audience="test",
)


def test_forged_token_rejected() -> None:
    with pytest.raises(MappedError) as exc:
        verify_bearer_token(VERIFIER, "forged.token.here")
    assert exc.value.code == ErrorCode.AUTHN_INVALID


def test_exchange_returns_openid_and_drops_session_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["grant_type"] == "authorization_code"
        assert request.url.params["js_code"] == "login-code"
        assert request.url.params["secret"] == "app-secret-value"
        return httpx.Response(200, json={"openid": "oid-1", "session_key": "SESSION_KEY"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        openid = exchange_code(VERIFIER, "login-code", client)
    assert openid == "oid-1"


def test_wechat_errcode_is_authn_invalid() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errcode": 40029, "errmsg": "invalid code"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(MappedError) as exc:
            exchange_code(VERIFIER, "bad", client)
    assert exc.value.code == ErrorCode.AUTHN_INVALID
    assert "invalid code" not in str(exc.value)


def test_route_mints_app_token_without_session_key(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["js_code"] == "abc"
        return httpx.Response(200, json={"openid": "oid-9", "session_key": "SESSION_KEY"})

    real_client = httpx.Client

    def _client(*_args: object, **_kwargs: object) -> httpx.Client:
        return real_client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(httpx, "Client", _client)
    app = FastAPI()
    settings = SimpleNamespace(
        wechat_app_id="wx-test",
        wechat_app_secret=SecretStr("app-secret-value"),
        jwt_secret=SecretStr(VERIFIER.secret),
        jwt_algorithm="HS256",
        jwt_issuer="test",
        jwt_audience="test",
        access_token_expire_minutes=5,
        api_v1_prefix="/api/v1",
    )
    register_auth_routes(app, settings)
    response = TestClient(app).post("/api/v1/session/wechat", json={"code": "abc"})
    assert response.status_code == 200
    body = response.json()
    assert "SESSION_KEY" not in response.text
    assert body["token_type"] == "Bearer"
    payload = jwt.decode(
        body["access_token"], VERIFIER.secret, algorithms=["HS256"], audience="test"
    )
    assert payload["sub"] == "oid-9"
    assert "session_key" not in payload


def test_deployed_rejects_dev_wechat_defaults() -> None:
    settings = SimpleNamespace(
        app_env="production",
        wechat_app_id=DEV_WECHAT_APP_ID,
        wechat_app_secret=SecretStr(DEV_WECHAT_APP_SECRET),
    )
    with pytest.raises(ValueError, match="WECHAT_APP_ID"):
        validate_identity_settings(settings)
