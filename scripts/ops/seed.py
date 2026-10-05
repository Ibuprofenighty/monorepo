#!/usr/bin/env python3
"""Seed data through controlled app capabilities (blueprint 09 §7).

- Uses the backend's own CLI entrypoint, never copies business rules.
- Only targets dev/test databases; refuses production.
- Idempotent: safe to re-run.

Usage: python scripts/ops/seed.py --env dev
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "apps" / "backend"

ENV_VARS = {"dev": "DATABASE_URL", "test": "TEST_DATABASE_URL"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--env",
        required=True,
        choices=list(ENV_VARS),
        help="explicit target environment (dev|test only)",
    )
    args = ap.parse_args()

    var = ENV_VARS[args.env]
    db_url = os.environ.get(var)
    if not db_url:
        print(f"refusing: {var} is not set for --env {args.env}")
        return 1
    if "prod" in db_url.lower():
        print("refusing: target looks like production")
        return 1

    env = {**os.environ, "DATABASE_URL": db_url}
    cmd = [sys.executable, "-m", "project_backend.entrypoints.cli", "seed"]
    print("+", " ".join(cmd), f"(env={args.env})")
    r = subprocess.run(cmd, cwd=BACKEND / "src", env=env)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
