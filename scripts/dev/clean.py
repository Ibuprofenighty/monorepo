#!/usr/bin/env python3
"""Delete only reproducible artifacts (blueprint 09 §8).

Never touches volumes, secrets, backups, lockfiles, node_modules or the uv venv.
Usage: python scripts/dev/clean.py [--dry-run]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CACHE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SKIP_DIRS = {".git", "node_modules", ".venv"}
BUILD_OUTPUTS = (
    "apps/miniprogram/dist",
    "apps/web/dist",
    "apps/web-next/.next",
    "apps/web-next/out",
    "apps/mobile/build",
    "apps/mobile/.dart_tool",
    "packages/dart/api_client/.dart_tool",
)


def targets() -> list[Path]:
    found: list[Path] = []
    stack = [ROOT]
    while stack:
        current = stack.pop()
        for child in current.iterdir():
            if not child.is_dir() or child.name in SKIP_DIRS:
                continue
            if child.name in CACHE_DIRS:
                found.append(child)
            else:
                stack.append(child)
    found.extend(p for rel in BUILD_OUTPUTS if (p := ROOT / rel).exists())
    return sorted(found)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="list what would be removed")
    args = ap.parse_args()
    for path in targets():
        print(("would remove " if args.dry_run else "remove ") + str(path.relative_to(ROOT)))
        if not args.dry_run:
            shutil.rmtree(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
