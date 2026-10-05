#!/usr/bin/env python3
"""Bootstrap: verify platform, tool versions, lockfiles and prerequisites.

Fails loudly on anything missing. Never installs secretly or prints secrets.
Usage: python scripts/dev/bootstrap.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"[bootstrap] FAIL: {msg}")


def ok(msg: str) -> None:
    print(f"[bootstrap] ok: {msg}")


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    p = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return p.returncode, (p.stdout + p.stderr).strip()


def check_tool(name: str, version_args: list[str], want: str = "") -> None:
    path = shutil.which(name)
    if not path:
        fail(f"tool {name!r} not found on PATH")
        return
    code, out = run([path, *version_args])
    first = out.splitlines()[0] if out else "?"
    if code != 0:
        fail(f"{name} --version failed: {first}")
    else:
        ok(f"{name} {first} {want}".rstrip())


def check_lock(rel: str, hint: str) -> None:
    p = ROOT / rel
    if p.exists():
        ok(f"lockfile {rel}")
    else:
        fail(f"missing lockfile {rel} ({hint})")


def main() -> int:
    # Tool banners may contain characters the console code page lacks (e.g. GBK).
    sys.stdout.reconfigure(errors="replace")  # type: ignore[union-attr]
    print("[bootstrap] root:", ROOT)
    ok(f"python {sys.version.split()[0]} (requires >= 3.12 per .python-version)")

    node_version = (ROOT / ".node-version").read_text(encoding="utf-8").strip()
    node = shutil.which("node")
    if not node:
        fail("tool 'node' not found on PATH")
    else:
        code, out = run([node, "--version"])
        got = out.splitlines()[0].strip() if out else ""
        want = "v" + node_version
        if code != 0 or got != want:
            fail(f"node {got or 'missing'} != {want} (.node-version)")
        else:
            ok(f"node {got}")
    check_tool("pnpm", ["--version"], "(need >= 9)")
    check_tool("uv", ["--version"])
    check_tool("docker", ["--version"])
    if (ROOT / "apps" / "mobile" / "pubspec.yaml").exists():
        check_tool("flutter", ["--version"], "(stable channel)")

    docker = shutil.which("docker")
    code, _ = run([docker, "compose", "version"]) if docker else (1, "")
    if code != 0:
        fail("docker compose plugin missing")
    else:
        ok("docker compose plugin")

    check_lock("pnpm-lock.yaml", "run: pnpm install --lockfile-only")
    check_lock("uv.lock", "run: uv lock (workspace root)")

    env_example = ROOT / ".env.example"
    env_file = ROOT / ".env"
    if not env_example.exists():
        fail(".env.example missing")
    else:
        ok(".env.example present")
    if env_file.exists():
        ok(".env present (never commit it)")
    else:
        print("[bootstrap] note: no .env — copy .env.example to .env for local dev")

    # Contracts prerequisites: openapi-typescript is a locked root devDependency;
    # datamodel-code-generator runs through uvx at the version pinned in generate.py.
    pnpm = shutil.which("pnpm")
    code, out = (
        run([pnpm, "exec", "openapi-typescript", "--version"], cwd=ROOT) if pnpm else (1, "")
    )
    if code != 0:
        fail("openapi-typescript not runnable (run: pnpm install --frozen-lockfile)")
    else:
        ok(f"openapi-typescript {out.splitlines()[-1] if out else '?'}")
    if not shutil.which("uvx"):
        fail("uvx not found (ships with uv)")

    if "DATABASE_URL" in os.environ or "TEST_DATABASE_URL" in os.environ:
        print("[bootstrap] note: DATABASE_URL/TEST_DATABASE_URL set in environment")

    if FAILURES:
        print(f"[bootstrap] {len(FAILURES)} failure(s) — fix them, then re-run")
        return 1
    print("[bootstrap] all prerequisites satisfied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
