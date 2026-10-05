"""AuthN verifier unit tests: the ONLY place Principals are minted (08 §4).

These test the real verify_bearer_token — no overrides, no mocks of the
boundary under test. check_counterexamples.py mutates the verifier and
expects test_forged_token_rejected to fail.
"""

from __future__ import annotations

import pytest
from project_backend.generated.http.errors import ErrorCode
from project_backend.platform.authn.verifiers.local import (
    Verifier,
    mint_token,
    verify_bearer_token,
)
from project_backend.platform.http.exception_handlers import MappedError

VERIFIER = Verifier(
    secret="test-secret-0123456789abcdef0123456789",
    algorithm="HS256",
    issuer="test",
    audience="test",
)


def test_missing_token_is_authn_required() -> None:
    with pytest.raises(MappedError) as e:
        verify_bearer_token(VERIFIER, None)
    assert e.value.code == ErrorCode.AUTHN_REQUIRED


def test_forged_token_rejected() -> None:
    with pytest.raises(MappedError) as e:
        verify_bearer_token(VERIFIER, "forged.token.here")
    assert e.value.code == ErrorCode.AUTHN_INVALID


def test_wrong_secret_rejected() -> None:
    other = Verifier(
        secret="other-secret-0123456789abcdef012345678",
        algorithm="HS256",
        issuer="test",
        audience="test",
    )
    token = mint_token(other, "u1", frozenset({"viewer"}), expires_minutes=5)
    with pytest.raises(MappedError) as e:
        verify_bearer_token(VERIFIER, token)
    assert e.value.code == ErrorCode.AUTHN_INVALID


def test_valid_token_mints_principal() -> None:
    token = mint_token(VERIFIER, "u1", frozenset({"editor"}), expires_minutes=5)
    p = verify_bearer_token(VERIFIER, token)
    assert p.subject == "u1"
    assert "editor" in p.roles
