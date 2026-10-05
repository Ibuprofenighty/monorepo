#!/usr/bin/env python3
"""Doctor: diagnose selected clients, tools, ports and external deps.

Read-only. Never prints secret values — only whether they are set.
Usage: python scripts/dev/doctor.py
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(cmd: list[str]) -> tuple[int, str]:
    exe = shutil.which(cmd[0])
    if exe is None:
        return 1, f"{cmd[0]} not found"
    try:
        p = subprocess.run(
            [exe, *cmd[1:]],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        out = (p.stdout + p.stderr).strip()
        first = out.splitlines()[0] if out else ""
        return p.returncode, first
    except Exception as e:  # noqa: BLE001 — diagnostic tool, report everything
        return 1, str(e)


def port_open(port: int) -> bool:
    s = socket.socket()
    s.settimeout(1)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def main() -> int:
    # Tool banners may contain characters the console code page lacks (e.g. GBK).
    sys.stdout.reconfigure(errors="replace")  # type: ignore[union-attr]
    print("== tools ==")
    for tool, args in (
        ("node", ["--version"]),
        ("pnpm", ["--version"]),
        ("uv", ["--version"]),
        ("docker", ["--version"]),
        ("flutter", ["--version"]),
        ("psql", ["--version"]),
    ):
        code, out = run([tool, *args])
        print(f"  {tool}: {out if code == 0 else 'missing'}")

    print("== workspace clients ==")
    for app in ("web", "web-next", "miniprogram", "mobile"):
        pkg = (ROOT / "apps" / app / "package.json").exists()
        pub = (ROOT / "apps" / app / "pubspec.yaml").exists()
        print(f"  apps/{app}: {'present' if pkg or pub else 'not selected/absent'}")

    print("== ports (local) ==")
    ports = [("api", 8000), ("web", 5173), ("postgres", 5432)]
    # begin capability:redis
    ports.append(("redis", 6379))
    # end capability:redis
    for name, port in ports:
        print(f"  {name}:{port} {'OPEN' if port_open(port) else 'closed'}")

    print("== external deps ==")
    code, _ = run(
        [
            "docker",
            "compose",
            "-f",
            "infra/compose/compose.yaml",
            "-f",
            "infra/compose/compose.dev.yaml",
            "ps",
            "--format",
            "{{.Name}}",
        ]
    )
    state = "running (see above)" if code == 0 else "compose not running / docker unavailable"
    print(f"  compose dev services: {state}")

    print("== env (presence only, values never printed) ==")
    for var in (
        "DATABASE_URL",
        "TEST_DATABASE_URL",
        "REDIS_URL",
        "APP_ENV",
        "JWT_SECRET",
        "MP_APPID",
        "MP_PRIVATE_KEY",
        "MP_API_BASE_URL",
    ):
        print(f"  {var}: {'set' if os.environ.get(var) else 'unset'}")

    print("== contracts ==")
    code, _ = run([sys.executable, "scripts/contracts/generate.py", "--check", "--quiet"])
    print(f"  generated drift check: {'clean' if code == 0 else 'DRIFT — run: make generate'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
