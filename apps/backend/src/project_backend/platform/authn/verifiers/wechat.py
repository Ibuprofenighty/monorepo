"""WeChat mini program login.

Official exchange: wx.login code (5 minutes, single use) is sent to
GET https://api.weixin.qq.com/sns/jscode2session
with appid, secret, js_code, grant_type=authorization_code.
The response openid becomes the session subject. session_key and the app
secret stay on the server; this module never returns them. The session
token is an application HS256 JWT, not a WeChat token.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from typing import Any

import httpx
import jwt
from pydantic import BaseModel

from project_backend.generated.http.errors import ErrorCode
from project_backend.kernel.errors import AuthenticationError
from project_backend.kernel.identity import Principal
from project_backend.platform.http.exception_handlers import MappedError

CODE2SESSION = "https://api.weixin.qq.com/sns/jscode2session"
DEV_WECHAT_APP_ID = "wx-dev-appid"
DEV_WECHAT_APP_SECRET = "dev-only-wechat-secret-never-deploy"
_DEPLOYED = frozenset({"staging", "production"})


class WechatCode(BaseModel):
    code: str


@dataclass(frozen=True)
class Verifier:
    app_id: str
    app_secret: str
    secret: str
    algorithm: str
    issuer: str
    audience: str


def verify_bearer_token(verifier: Verifier, token: str | None) -> Principal:
    if not token:
        raise MappedError(ErrorCode.AUTHN_REQUIRED)
    try:
        payload = jwt.decode(
            token,
            verifier.secret,
            algorithms=[verifier.algorithm],
            issuer=verifier.issuer,
            audience=verifier.audience,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as e:
        raise MappedError(ErrorCode.AUTHN_INVALID) from e
    roles = payload.get("roles", [])
    if not isinstance(roles, list):
        raise AuthenticationError("roles claim malformed")
    return Principal(subject=str(payload["sub"]), roles=frozenset(str(r) for r in roles))


def mint_token(
    verifier: Verifier, subject: str, roles: frozenset[str], expires_minutes: int
) -> str:
    from datetime import datetime, timedelta

    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": subject,
            "roles": sorted(roles),
            "iss": verifier.issuer,
            "aud": verifier.audience,
            "iat": now,
            "exp": now + timedelta(minutes=expires_minutes),
        },
        verifier.secret,
        algorithm=verifier.algorithm,
    )


def exchange_code(verifier: Verifier, code: str, client: httpx.Client) -> str:
    """Return the openid. session_key is discarded and never returned."""
    if not code:
        raise MappedError(ErrorCode.AUTHN_INVALID)
    response = client.get(
        CODE2SESSION,
        params={
            "appid": verifier.app_id,
            "secret": verifier.app_secret,
            "js_code": code,
            "grant_type": "authorization_code",
        },
        timeout=5.0,
    )
    try:
        data = response.json()
    except ValueError as e:
        raise MappedError(ErrorCode.AUTHN_INVALID) from e
    if not isinstance(data, dict) or data.get("errcode", 0):
        raise MappedError(ErrorCode.AUTHN_INVALID)
    data.pop("session_key", None)
    openid = data.get("openid")
    if not isinstance(openid, str) or not openid:
        raise MappedError(ErrorCode.AUTHN_INVALID)
    return openid


def validate_identity_settings(settings: Any) -> None:
    secret = settings.wechat_app_secret
    raw = secret.get_secret_value() if hasattr(secret, "get_secret_value") else str(secret)
    if settings.app_env not in _DEPLOYED:
        return
    if settings.wechat_app_id == DEV_WECHAT_APP_ID or not settings.wechat_app_id:
        raise ValueError(f"WECHAT_APP_ID must be injected when APP_ENV={settings.app_env}")
    if raw == DEV_WECHAT_APP_SECRET or not raw:
        raise ValueError(f"WECHAT_APP_SECRET must be injected when APP_ENV={settings.app_env}")


def build_verifier(settings: Any) -> Verifier:
    secret = settings.wechat_app_secret
    raw = secret.get_secret_value() if hasattr(secret, "get_secret_value") else str(secret)
    return Verifier(
        app_id=settings.wechat_app_id,
        app_secret=raw,
        secret=settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


def register_auth_routes(app: Any, settings: Any) -> None:
    from fastapi import APIRouter

    router = APIRouter()

    @router.post("/session/wechat")
    def create_wechat_session(body: WechatCode) -> dict[str, str | int]:
        verifier = build_verifier(settings)
        with httpx.Client() as client:
            openid = exchange_code(verifier, body.code, client)
        minutes = settings.access_token_expire_minutes
        token = mint_token(verifier, openid, frozenset(), minutes)
        return {"access_token": token, "token_type": "Bearer", "expires_in": minutes * 60}

    app.include_router(router, prefix=settings.api_v1_prefix)
