"""Keycloak access tokens, validated locally.

The realm publishes JWK at
{issuer}/protocol/openid-connect/certs. Tokens are RS256. iss is the realm
URL (https://host/realms/{realm}), aud is the configured audience, and the
payload typ must be Bearer. realm_access.roles becomes Principal.roles.
This service does not mint tokens and does not call the introspection endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jwt

from project_backend.generated.http.errors import ErrorCode
from project_backend.kernel.errors import AuthenticationError
from project_backend.kernel.identity import Principal
from project_backend.platform.authn.protocol import UnsupportedMint
from project_backend.platform.http.exception_handlers import MappedError

DEV_KEYCLOAK_ISSUER = "https://keycloak.invalid/realms/dev"
DEV_KEYCLOAK_AUDIENCE = "project-api"
_DEPLOYED = frozenset({"staging", "production"})


@dataclass(frozen=True)
class Verifier:
    issuer: str
    audience: str
    jwks: Any


def verify_bearer_token(verifier: Verifier, token: str | None) -> Principal:
    if not token:
        raise MappedError(ErrorCode.AUTHN_REQUIRED)
    try:
        key = verifier.jwks.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            issuer=verifier.issuer,
            audience=verifier.audience,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as e:
        raise MappedError(ErrorCode.AUTHN_INVALID) from e
    if payload.get("typ") != "Bearer":
        raise MappedError(ErrorCode.AUTHN_INVALID)
    realm = payload.get("realm_access")
    roles: list[str] = []
    if realm is not None:
        if not isinstance(realm, dict) or not isinstance(realm.get("roles"), list):
            raise AuthenticationError("realm_access.roles malformed")
        roles = [str(role) for role in realm["roles"]]
    return Principal(subject=str(payload["sub"]), roles=frozenset(roles))


def mint_token(
    verifier: Verifier, subject: str, roles: frozenset[str], expires_minutes: int
) -> str:
    del verifier, subject, roles, expires_minutes
    raise UnsupportedMint("keycloak issues access tokens; this service does not mint them")


def validate_identity_settings(settings: Any) -> None:
    issuer = str(settings.keycloak_issuer).rstrip("/")
    if not issuer.startswith("https://") or "/realms/" not in issuer:
        raise ValueError("KEYCLOAK_ISSUER must be https://<host>/realms/<realm>")
    if not settings.keycloak_audience:
        raise ValueError("KEYCLOAK_AUDIENCE is required")
    if settings.app_env in _DEPLOYED and issuer == DEV_KEYCLOAK_ISSUER:
        raise ValueError(f"KEYCLOAK_ISSUER must be injected when APP_ENV={settings.app_env}")


def build_verifier(settings: Any) -> Verifier:
    issuer = str(settings.keycloak_issuer).rstrip("/")
    url = f"{issuer}/protocol/openid-connect/certs"
    return Verifier(
        issuer=issuer,
        audience=str(settings.keycloak_audience),
        jwks=jwt.PyJWKClient(url),
    )


def register_auth_routes(app: Any, settings: Any) -> None:
    """Keycloak issues the token; this service only verifies it."""
    del app, settings
