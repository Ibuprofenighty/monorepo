#!/usr/bin/env python3
"""Makefile `verify` is the merge gate. CI may only run those targets.

Lockfile installs are setup, not a second test suite. checkout, setup actions,
and artifact upload are not `run` steps, so they are outside this comparison.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SETUP_RUNS = frozenset(
    {
        "pnpm install --frozen-lockfile",
        "uv sync --frozen --package project-backend --extra dev",
    }
)


def verify_targets(makefile: str) -> set[str]:
    names: set[str] = set()
    for line in makefile.splitlines():
        if not line.startswith("verify:"):
            continue
        body = line.split("##", 1)[0][len("verify:") :]
        names.update(body.split())
    return names


def ci_runs(workflow: str) -> tuple[set[str], list[str]]:
    targets: set[str] = set()
    errors: list[str] = []
    for match in re.finditer(r"(?m)^[ \t]*(?:-[ \t]*)?run:[ \t]*(.+)$", workflow):
        command = match.group(1).strip()
        if command in SETUP_RUNS:
            continue
        if not command.startswith("make "):
            errors.append(f"ci.yaml run is not a verify target: {command}")
            continue
        args = command.split()[1:]
        if not args or any(arg.startswith("-") for arg in args):
            errors.append(f"ci.yaml run is not a bare make target list: {command}")
            continue
        targets.update(args)
    return targets, errors


def main() -> int:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yaml").read_text(encoding="utf-8")
    expected = verify_targets(makefile)
    actual, errors = ci_runs(workflow)
    if not expected:
        errors.append("Makefile has no verify prerequisites")
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        errors.append("CI does not run: " + " ".join(missing))
    if extra:
        errors.append("CI runs targets outside verify: " + " ".join(extra))
    if errors:
        print("GATE CHECK FAILURES:")
        for err in errors:
            print(" ", err)
        return 1
    print(f"check-gate: ok ({len(expected)} targets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
