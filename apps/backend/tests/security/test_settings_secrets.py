"""Deployed environments must never run with the built-in dev JWT secret (08 §7)."""

from __future__ import annotations

import pytest
from project_backend.platform.config.settings import DEV_JWT_SECRET, Settings
from pydantic import ValidationError

STRONG = "s" * 32


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)


@pytest.mark.parametrize("env", ["staging", "production"])
def test_deployed_env_rejects_default_secret(env: str) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET must be injected"):
        Settings(app_env=env, _env_file=None)


@pytest.mark.parametrize("env", ["staging", "production"])
def test_deployed_env_rejects_short_secret(env: str) -> None:
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(app_env=env, jwt_secret="short-secret", _env_file=None)


@pytest.mark.parametrize("env", ["staging", "production"])
def test_deployed_env_accepts_injected_secret(env: str) -> None:
    s = Settings(app_env=env, jwt_secret=STRONG, _env_file=None)
    assert s.jwt_secret.get_secret_value() == STRONG


@pytest.mark.parametrize("env", ["dev", "test"])
def test_dev_and_test_may_use_dev_secret(env: str) -> None:
    s = Settings(app_env=env, _env_file=None)
    assert s.jwt_secret.get_secret_value() == DEV_JWT_SECRET


def test_secret_is_not_rendered_in_repr() -> None:
    s = Settings(app_env="production", jwt_secret=STRONG, _env_file=None)
    assert STRONG not in repr(s)
