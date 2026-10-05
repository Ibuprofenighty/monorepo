"""Keycloak JWKS verification. The signing key is local; nothing calls a realm."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from project_backend.generated.http.errors import ErrorCode
from project_backend.platform.authn.protocol import UnsupportedMint
from project_backend.platform.authn.verifiers.keycloak import (
    DEV_KEYCLOAK_ISSUER,
    Verifier,
    mint_token,
    validate_identity_settings,
    verify_bearer_token,
)
from project_backend.platform.http.exception_handlers import MappedError

ISSUER = "https://keycloak.invalid/realms/dev"
AUDIENCE = "project-api"
_PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _Key:
    def __init__(self, key: object) -> None:
        self.key = key


class _JWKS:
    def get_signing_key_from_jwt(self, token: str) -> _Key:
        del token
        return _Key(_PRIVATE.public_key())


VERIFIER = Verifier(issuer=ISSUER, audience=AUDIENCE, jwks=_JWKS())


def _token(**overrides: object) -> str:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": "user-1",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "typ": "Bearer",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "realm_access": {"roles": ["editor"]},
    }
    payload.update(overrides)
    return jwt.encode(payload, _PRIVATE, algorithm="RS256")


def test_forged_token_rejected() -> None:
    with pytest.raises(MappedError) as exc:
        verify_bearer_token(VERIFIER, "forged.token.here")
    assert exc.value.code == ErrorCode.AUTHN_INVALID


def test_valid_access_token_maps_realm_roles() -> None:
    principal = verify_bearer_token(VERIFIER, _token())
    assert principal.subject == "user-1"
    assert principal.roles == frozenset({"editor"})


def test_wrong_audience_rejected() -> None:
    with pytest.raises(MappedError) as exc:
        verify_bearer_token(VERIFIER, _token(aud="other"))
    assert exc.value.code == ErrorCode.AUTHN_INVALID


def test_typ_must_be_bearer() -> None:
    with pytest.raises(MappedError) as exc:
        verify_bearer_token(VERIFIER, _token(typ="Refresh"))
    assert exc.value.code == ErrorCode.AUTHN_INVALID


def test_mint_is_refused() -> None:
    with pytest.raises(UnsupportedMint):
        mint_token(VERIFIER, "user-1", frozenset(), 5)


def test_deployed_rejects_placeholder_issuer() -> None:
    settings = SimpleNamespace(
        app_env="production",
        keycloak_issuer=DEV_KEYCLOAK_ISSUER,
        keycloak_audience=AUDIENCE,
    )
    with pytest.raises(ValueError, match="KEYCLOAK_ISSUER"):
        validate_identity_settings(settings)
