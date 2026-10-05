"""Local HS256 bearer tokens. The only Principal mint for identity: local."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from typing import Any

import jwt

from project_backend.generated.http.errors import ErrorCode
from project_backend.kernel.errors import AuthenticationError
from project_backend.kernel.identity import Principal
from project_backend.platform.http.exception_handlers import MappedError


@dataclass(frozen=True)
class Verifier:
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


def build_verifier(settings: Any) -> Verifier:
    return Verifier(
        secret=settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


def register_auth_routes(app: Any, settings: Any) -> None:
    """Local identity has no login route; callers present a bearer token."""
    del app, settings
