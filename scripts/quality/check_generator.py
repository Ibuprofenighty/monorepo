#!/usr/bin/env python3
"""Fast generator gate. Copies three profiles and checks each copy.

Profiles: the two few-shot answers (both keep redis and worker) and one
local web-vite project with no capabilities. The empty profile is what proves
redis/arq are removed and the lock is rewritten.

Does not run flutter create or pnpm install. Missing docker, pnpm, or uv fails
the gate. Spectral uses the mother template's ruleset.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "scaffold"))
from create_project import (  # noqa: E402
    copy_tree,
    load_answers,
    rename_python_package,
    tool,
    validate,
)
from selection import apply_selection  # noqa: E402

FEW_SHOTS = (
    ROOT / "examples" / "answers-miniprogram.yaml",
    ROOT / "examples" / "answers-web-mobile.yaml",
)
EMPTY = {
    "project_name": "gate-local",
    "python_package": "gate_local",
    "ts_scope": "gate-local",
    "clients": ["web-vite"],
    "identity": "local",
    "authz": "local",
    "capabilities": [],
    "git_init": False,
}
_ENV = """POSTGRES_PASSWORD=gate-pw
JWT_SECRET=gate-jwt-secret-not-deployed-0000
WECHAT_APP_ID=wx-gate
WECHAT_APP_SECRET=gate-wechat-secret-not-deployed
KEYCLOAK_ISSUER=https://keycloak.example/realms/project
KEYCLOAK_AUDIENCE=project-api
"""


def _run(cmd: list[str], cwd: Path, timeout: int) -> None:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if result.returncode != 0:
        print(result.stdout[-3000:], file=sys.stderr)
        print(result.stderr[-3000:], file=sys.stderr)
        tail = " ".join(cmd[-6:])
        sys.exit(f"[check-generator] ERROR: {tail} failed")


def _dep_lines(text: str, name: str) -> bool:
    prefix = f'"{name}'
    return any(line.strip().startswith(prefix) for line in text.splitlines())


def _assert_lock(target: Path, answers: dict, label: str) -> None:
    caps = list(answers.get("capabilities") or [])
    pyproject = (target / "apps" / "backend" / "pyproject.toml").read_text(encoding="utf-8")
    lock = (target / "uv.lock").read_text(encoding="utf-8")
    dist = answers["python_package"].replace("_", "-")
    if f'name = "{dist}"' not in lock:
        sys.exit(f"[check-generator] ERROR: {label} lock is missing {dist}")
    for dep, cap in (("redis", "redis"), ("arq", "worker")):
        in_py = _dep_lines(pyproject, dep)
        in_lock = f'name = "{dep}"' in lock
        if cap in caps and not (in_py and in_lock):
            sys.exit(f"[check-generator] ERROR: {label} dropped selected {dep}")
        if cap not in caps and (in_py or in_lock):
            sys.exit(f"[check-generator] ERROR: {label} still contains unselected {dep}")


def _spectral(spec: Path) -> None:
    ruleset = str(ROOT / ".spectral.yaml")
    _run([tool("pnpm"), "exec", "spectral", "lint", str(spec), "--ruleset", ruleset], ROOT, 180)


def _compose(target: Path, label: str) -> None:
    env = target / ".env"
    env.write_text(_ENV, encoding="utf-8", newline="\n")
    base = target / "infra" / "compose" / "compose.yaml"
    overlay = target / "infra" / "compose" / "compose.test.yaml"
    project = f"gate-{label}"
    base_cmd = ["docker", "compose", "--env-file", str(env), "-p", project, "-f", str(base)]
    _run([*base_cmd, "config", "-q"], target, 120)
    _run([*base_cmd, "-f", str(overlay), "config", "-q"], target, 120)


def _ruff(target: Path) -> None:
    uv = tool("uv")
    cwd = target / "apps" / "backend"
    paths = ["src", "tests", "../../scripts"]
    # Rename changes import order. The same ruff fix + format create_project runs
    # must leave a tree that passes check and format --check.
    steps = (
        ["check", "--fix", "--exit-zero", *paths],
        ["format", *paths],
        ["check", *paths],
        ["format", "--check", *paths],
    )
    for args in steps:
        _run([uv, "run", "--frozen", "--extra", "dev", "ruff", *args], cwd, 900)


def _gate(answers: dict, label: str) -> None:
    print(f"[check-generator] {label}", flush=True)
    try:
        with tempfile.TemporaryDirectory(prefix="forge-gate-") as raw:
            target = Path(raw) / answers["project_name"]
            target.mkdir()
            copy_tree(target, answers["clients"])
            rename_python_package(target, answers["python_package"])
            apply_selection(target, answers)
            _assert_lock(target, answers, label)
            _spectral(target / "contracts" / "http" / "openapi.yaml")
            _compose(target, label)
            _ruff(target)
    except SystemExit as exc:
        if str(exc).startswith("[check-generator]"):
            raise
        raise SystemExit(f"[check-generator] {label}: {exc}") from exc
    print(f"[check-generator] {label}: PASS", flush=True)


def main() -> int:
    for name in ("docker", "pnpm", "uv"):
        if shutil.which(name) is None:
            sys.exit(f"[check-generator] ERROR: {name} is required")
    probe = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if probe.returncode != 0:
        print(probe.stderr[-1000:], file=sys.stderr)
        sys.exit("[check-generator] ERROR: docker compose is required")
    for path in FEW_SHOTS:
        _gate(validate(load_answers(path)), path.stem)
    _gate(validate(dict(EMPTY)), "empty-capabilities")
    return 0


if __name__ == "__main__":
    sys.exit(main())
