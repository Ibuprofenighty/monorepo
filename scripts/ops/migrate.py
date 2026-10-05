#!/usr/bin/env python3
"""Single controlled migration against an explicit environment (blueprint 09 §9).

Usage: python scripts/ops/migrate.py --env dev|staging|production [--to REV] [--sql]

- Never runs without --env. Production requires typed confirmation.
- Delegates to alembic inside apps/backend; this script only enforces the gate.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "apps" / "backend"

ENV_VARS = {
    "dev": "DATABASE_URL",
    "staging": "STAGING_DATABASE_URL",
    "production": "PRODUCTION_DATABASE_URL",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--env",
        required=True,
        choices=list(ENV_VARS),
        help="explicit target environment (no default)",
    )
    ap.add_argument("--to", default="head", help="alembic revision (default: head)")
    ap.add_argument("--sql", action="store_true", help="print SQL instead of applying")
    args = ap.parse_args()

    var = ENV_VARS[args.env]
    if not os.environ.get(var):
        print(f"refusing: {var} is not set for --env {args.env}")
        return 1

    if args.env == "production" and not args.sql:
        answer = input("Type the environment name to confirm migration on PRODUCTION: ")
        if answer.strip() != "production":
            print("aborted: confirmation mismatch")
            return 1

    cmd = [sys.executable, "-m", "alembic", "upgrade", args.to]
    if args.sql:
        cmd.append("--sql")
    print("+", " ".join(cmd), f"(env={args.env})")
    env = {**os.environ, "DATABASE_URL": os.environ[var]}
    r = subprocess.run(cmd, cwd=BACKEND, env=env)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
