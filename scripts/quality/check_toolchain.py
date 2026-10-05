#!/usr/bin/env python3
"""Toolchain pins: each version file is the authority; copies must match it.

The gate does not query a registry. The Node digest below is the manifest-list
(index) digest of node:<version>-bookworm-slim, not a single-platform blob
and not the floating node:24 tag. Update that map in the same change as
.node-version.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Index digest from `docker buildx imagetools inspect node:24.11.1-bookworm-slim`.
PINNED_INDEX_DIGESTS = {
    "24.11.1": "sha256:48abc13a19400ca3985071e287bd405a1d99306770eb81d61202fb6b65cf0b57",
}


def version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def at_least(pinned: str, floor: str) -> bool:
    left = version_tuple(pinned)
    right = version_tuple(floor)
    width = max(len(left), len(right))
    left = left + (0,) * (width - len(left))
    right = right + (0,) * (width - len(right))
    return left >= right


def action_shas(text: str) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for uses, sha in re.findall(
        r"uses:\s*([\w.-]+/[\w.-]+(?:/[\w.-]+)*)@([0-9a-f]{40})",
        text,
    ):
        repo = "/".join(uses.split("/")[:2])
        found.setdefault(repo, set()).add(sha)
    return found


def main() -> int:
    errors: list[str] = []
    version = (ROOT / ".node-version").read_text(encoding="utf-8").strip()
    digest = PINNED_INDEX_DIGESTS.get(version)
    if digest is None:
        errors.append(f".node-version {version} has no recorded index digest in check_toolchain.py")
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    engines = package["engines"]["node"]
    if engines != version:
        errors.append(f"package.json engines.node {engines!r} != .node-version {version!r}")
    manager = package.get("packageManager", "")
    if re.fullmatch(r"pnpm@\d+\.\d+\.\d+", manager) is None:
        errors.append(f"package.json packageManager {manager!r} is not an exact pnpm version")

    ci = (ROOT / ".github/workflows/ci.yaml").read_text(encoding="utf-8")
    if re.search(r"(?<![\w-])node-version:", ci):
        errors.append("ci.yaml must not set node-version; use node-version-file: .node-version")
    if "node-version-file: .node-version" not in ci:
        errors.append("ci.yaml must set node-version-file: .node-version")

    for block in re.split(r"\n\s*- ", ci):
        if "pnpm/action-setup@" in block and re.search(r"\bversion:", block):
            errors.append(
                "pnpm/action-setup must not set version; package.json packageManager is the pin"
            )
        if "subosito/flutter-action@" in block:
            if "flutter-version-file: .flutter-version" not in block:
                errors.append("flutter-action must set flutter-version-file: .flutter-version")
            if re.search(r"\bchannel:", block):
                errors.append("flutter-action must not set channel; .flutter-version is the pin")

    docker = (ROOT / "infra/docker/web.Dockerfile").read_text(encoding="utf-8")
    if digest is not None:
        if f"ARG NODE_VERSION={version}\n" not in docker:
            errors.append(f"web.Dockerfile ARG NODE_VERSION is not {version}")
        if f"ARG NODE_DIGEST={digest}\n" not in docker:
            errors.append("web.Dockerfile ARG NODE_DIGEST is not the recorded index digest")
        from_line = "FROM node:${NODE_VERSION}-bookworm-slim@${NODE_DIGEST}"
        if docker.count(from_line) != 2:
            errors.append(f"web.Dockerfile must use {from_line} exactly twice")

    python = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    backend = (ROOT / "infra/docker/backend.Dockerfile").read_text(encoding="utf-8")
    if f"ARG PYTHON_VERSION={python}\n" not in backend:
        errors.append(f"backend.Dockerfile ARG PYTHON_VERSION is not {python}")

    flutter_path = ROOT / ".flutter-version"
    if not flutter_path.is_file():
        errors.append(".flutter-version is missing")
        flutter = ""
    else:
        flutter = flutter_path.read_text(encoding="utf-8").strip()
        if re.fullmatch(r"\d+\.\d+\.\d+", flutter) is None:
            errors.append(f".flutter-version {flutter!r} is not major.minor.patch")
    mobile_path = ROOT / "apps/mobile/pubspec.yaml"
    if mobile_path.is_file():
        environment = mobile_path.read_text(encoding="utf-8").split("\ndependencies:", 1)[0]
        floor = re.search(r'flutter:\s*"?(>=(\d+\.\d+\.\d+))"?', environment)
        if floor is None:
            errors.append("apps/mobile/pubspec.yaml has no flutter: >=x.y.z floor")
        elif flutter and not at_least(flutter, floor.group(2)):
            errors.append(f".flutter-version {flutter} is below pubspec floor {floor.group(2)}")
    elif "subosito/flutter-action@" in ci:
        errors.append("flutter-action is set but apps/mobile/pubspec.yaml is missing")

    compose = (ROOT / "infra/compose/compose.yaml").read_text(encoding="utf-8")
    for name in ("postgres", "redis"):
        composed = re.findall(rf"image:\s*({name}:\S+)", compose)
        wired = re.findall(rf"image:\s*({name}:\S+)", ci)
        if composed != wired:
            errors.append(f"ci.yaml {name} images {wired} != compose.yaml {composed}")

    shas: dict[str, set[str]] = {}
    for path in sorted((ROOT / ".github/workflows").glob("*.yaml")):
        for repo, pins in action_shas(path.read_text(encoding="utf-8")).items():
            shas.setdefault(repo, set()).update(pins)
    for repo, pins in sorted(shas.items()):
        if len(pins) > 1:
            errors.append(f"{repo} is pinned to more than one SHA: {sorted(pins)}")

    if errors:
        print("TOOLCHAIN CHECK FAILURES:")
        for err in errors:
            print(" ", err)
        return 1
    print(f"check-toolchain: ok (node {version}, python {python}, flutter {flutter}, {manager})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
