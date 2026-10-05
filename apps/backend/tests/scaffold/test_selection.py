"""Generate-time identity and capability rules."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts" / "scaffold"))
from selection import (  # noqa: E402
    apply_markers,
    apply_selection,
    check_selection,
    prune_dependency_text,
)


def test_constraints() -> None:
    with pytest.raises(SystemExit, match="wechat"):
        check_selection({"identity": "local", "clients": ["wechat-native"], "capabilities": []})
    with pytest.raises(SystemExit, match="worker requires redis"):
        check_selection({"identity": "local", "clients": ["web-vite"], "capabilities": ["worker"]})
    with pytest.raises(SystemExit, match="no canonical implementation"):
        check_selection(
            {"identity": "keycloak", "clients": ["web-vite"], "capabilities": ["storage"]}
        )
    with pytest.raises(SystemExit, match="not implemented"):
        check_selection({"identity": "aws", "clients": ["web-vite"], "capabilities": []})
    check_selection(
        {
            "identity": "wechat",
            "clients": ["wechat-native"],
            "capabilities": ["redis", "worker"],
        }
    )


def test_prune_dependency_text_matches_backend_pyproject() -> None:
    src = (ROOT / "apps" / "backend" / "pyproject.toml").read_text(encoding="utf-8")
    assert prune_dependency_text(src, ["redis", "worker"]) == src
    redis_only = prune_dependency_text(src, ["redis"])
    assert '"arq>=' not in redis_only
    assert '"redis>=' in redis_only
    assert '"pyjwt[crypto]>=' in redis_only
    none = prune_dependency_text(src, [])
    assert '"arq>=' not in none and '"redis>=' not in none
    assert '"fastapi>=' in none and '"uvicorn[standard]>=' in none


def test_markers_drop_disabled_regions_and_keep_the_rest() -> None:
    text = "\n".join(
        [
            "keep",
            "# begin capability:worker",
            "worker",
            "# begin identity:hs256",
            "jwt",
            "# end identity:hs256",
            "# end capability:worker",
            "# begin capability:redis",
            "redis",
            "# end capability:redis",
            "",
        ]
    )
    kept = apply_markers(text, set())
    assert "worker" in kept and "jwt" in kept and "redis" in kept
    assert "# begin" not in kept
    stripped = apply_markers(text, {"capability:worker", "capability:redis"})
    assert stripped.strip() == "keep"


def test_real_compose_markers_balance() -> None:
    compose = (ROOT / "infra" / "compose" / "compose.yaml").read_text(encoding="utf-8")
    full = apply_markers(compose, set())
    assert "image: redis:7-bookworm" in full
    assert "JWT_SECRET" in full
    assert "# begin" not in full
    no_redis = apply_markers(compose, {"capability:redis", "capability:worker"})
    assert "image: redis" not in no_redis
    assert "worker:" not in no_redis
    assert "postgres:" in no_redis
    keycloak = apply_markers(compose, {"identity:hs256"})
    assert "JWT_SECRET:" not in keycloak
    assert "DATABASE_URL" in keycloak


def test_apply_selection_keeps_only_wechat() -> None:
    tmp = tempfile.TemporaryDirectory(dir=ROOT, ignore_cleanup_errors=True)
    try:
        _assert_wechat_selection(Path(tmp.name))
    finally:
        tmp.cleanup()


def _assert_wechat_selection(tmp_path: Path) -> None:
    pkg = "sample_backend"
    src = tmp_path / "apps" / "backend" / "src" / pkg
    authn = src / "platform" / "authn"
    (authn / "verifiers").mkdir(parents=True)
    (authn / "active.py").write_text(
        "from sample_backend.platform.authn.verifiers.local import Verifier\n",
        encoding="utf-8",
        newline="\n",
    )
    for name in ("local", "wechat", "keycloak"):
        (authn / "verifiers" / f"{name}.py").write_text(f"# {name}\n", encoding="utf-8")
    security = tmp_path / "apps" / "backend" / "tests" / "security"
    security.mkdir(parents=True)
    for fname in (
        "test_authn_verifier.py",
        "test_wechat_verifier.py",
        "test_keycloak_verifier.py",
        "test_verifier_exports.py",
        "test_settings_secrets.py",
    ):
        (security / fname).write_text("# test\n", encoding="utf-8")
    settings = src / "platform" / "config"
    settings.mkdir(parents=True)
    (settings / "settings.py").write_text(
        "from pydantic import SecretStr, model_validator\n"
        "class Settings:\n"
        "    # begin identity\n"
        "    jwt_secret: str = 'x'\n"
        "    # end identity\n",
        encoding="utf-8",
        newline="\n",
    )
    (tmp_path / "scripts" / "quality").mkdir(parents=True)
    (tmp_path / "scripts" / "quality" / "check_counterexamples.py").write_text(
        'file=Path("platform/authn/verifiers/local.py")\n'
        '"tests/security/test_authn_verifier.py::test_forged_token_rejected"\n',
        encoding="utf-8",
        newline="\n",
    )
    (tmp_path / "contracts" / "http").mkdir(parents=True)
    (tmp_path / "Makefile").write_text(
        "verify: check-contract\n"
        "# begin template-only\n"
        "verify: check-generator\n"
        "# end template-only\n",
        encoding="utf-8",
        newline="\n",
    )
    (tmp_path / "contracts" / "http" / "openapi.yaml").write_text(
        "openapi: 3.1.0\npaths:\n  /health:\n    get: {}\ncomponents:\n  schemas: {}\n",
        encoding="utf-8",
        newline="\n",
    )
    apply_selection(
        tmp_path,
        {
            "identity": "wechat",
            "python_package": pkg,
            "capabilities": ["redis", "worker"],
            "clients": ["wechat-native"],
        },
    )
    active = (authn / "active.py").read_text(encoding="utf-8")
    assert "verifiers.wechat" in active
    assert not (authn / "verifiers" / "local.py").exists()
    assert (authn / "verifiers" / "wechat.py").exists()
    assert not (security / "test_authn_verifier.py").exists()
    assert (security / "test_wechat_verifier.py").exists()
    assert not (security / "test_verifier_exports.py").exists()
    spec = (tmp_path / "contracts" / "http" / "openapi.yaml").read_text(encoding="utf-8")
    assert "/api/v1/session/wechat:" in spec
    rendered = (settings / "settings.py").read_text(encoding="utf-8")
    assert "wechat_app_id" in rendered
    assert "DEV_WECHAT_APP_ID" in rendered
    makefile = (tmp_path / "Makefile").read_text(encoding="utf-8")
    assert "check-contract" in makefile
    assert "check-generator" not in makefile
    assert "# begin" not in makefile
