#!/usr/bin/env python3
"""Node pin: .node-version is the version; the web image digest is recorded here.

The gate does not query a registry. The digest below is the manifest-list
(index) digest of node:<version>-bookworm-slim, not a single-platform blob
and not the floating node:24 tag. Update the map in the same change as
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


def main() -> int:
    errors: list[str] = []
    version = (ROOT / ".node-version").read_text(encoding="utf-8").strip()
    digest = PINNED_INDEX_DIGESTS.get(version)
    if digest is None:
        errors.append(f".node-version {version} has no recorded index digest in check_toolchain.py")
    engines = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["engines"]["node"]
    if engines != version:
        errors.append(f"package.json engines.node {engines!r} != .node-version {version!r}")

    ci = (ROOT / ".github/workflows/ci.yaml").read_text(encoding="utf-8")
    pins = re.findall(r"node-version:\s*([^\s,}]+)", ci)
    if not pins:
        errors.append("ci.yaml has no node-version")
    elif any(pin != version for pin in pins):
        errors.append(f"ci.yaml node-version values {pins} != {version}")

    docker = (ROOT / "infra/docker/web.Dockerfile").read_text(encoding="utf-8")
    if digest is not None:
        if f"ARG NODE_VERSION={version}\n" not in docker:
            errors.append(f"web.Dockerfile ARG NODE_VERSION is not {version}")
        if f"ARG NODE_DIGEST={digest}\n" not in docker:
            errors.append("web.Dockerfile ARG NODE_DIGEST is not the recorded index digest")
        from_line = "FROM node:${NODE_VERSION}-bookworm-slim@${NODE_DIGEST}"
        if docker.count(from_line) != 2:
            errors.append(f"web.Dockerfile must use {from_line} exactly twice")

    if errors:
        print("TOOLCHAIN CHECK FAILURES:")
        for err in errors:
            print(" ", err)
        return 1
    print(f"check-toolchain: ok (node {version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
