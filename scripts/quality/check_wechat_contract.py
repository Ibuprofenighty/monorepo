#!/usr/bin/env python3
"""Spectral-lint the OpenAPI document after the wechat session splice.

The mother contract does not declare POST /api/v1/session/wechat. The generator
inserts that path only for wechat projects. This gate lints a temporary copy
and does not modify contracts/http/openapi.yaml.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "scaffold"))
from selection import _splice_wechat_openapi  # noqa: E402


def main() -> int:
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        sys.exit("[check-contract] ERROR: pnpm is required")
    with tempfile.TemporaryDirectory(prefix="forge-wechat-contract-") as raw:
        target = Path(raw)
        dest = target / "contracts" / "http"
        dest.mkdir(parents=True)
        shutil.copy2(ROOT / "contracts" / "http" / "openapi.yaml", dest / "openapi.yaml")
        _splice_wechat_openapi(target)
        spec = dest / "openapi.yaml"
        if "/api/v1/session/wechat:" not in spec.read_text(encoding="utf-8"):
            sys.exit("[check-contract] ERROR: wechat session path was not spliced")
        ruleset = str(ROOT / ".spectral.yaml")
        result = subprocess.run(
            [pnpm, "exec", "spectral", "lint", str(spec), "--ruleset", ruleset],
            cwd=ROOT,
            timeout=180,
        )
        if result.returncode != 0:
            sys.exit("[check-contract] ERROR: wechat-spliced OpenAPI failed Spectral")
    print("[check-contract] wechat-spliced OpenAPI: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
