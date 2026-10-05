#!/usr/bin/env python3
"""Breaking-change gate for the hand-written contract (blueprint 02 §8).

Compares contracts/http/openapi.yaml (working tree) against the version in
git HEAD using oasdiff. Fails on breaking changes unless the change is
explicitly approved.

Approval: set env BREAKING_CHANGE_APPROVED=1 with a justification in the
commit message containing "BREAKING:". This keeps the approval visible in
history instead of hidden in CI config.

Usage: python scripts/quality/check_breaking.py
"""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "contracts" / "http" / "openapi.yaml"
OASDIFF_VERSION = "v1.33.0"
BIN_DIR = ROOT / ".tools" / "bin"
# sha256 of the release archives, from that tag's checksums.txt. The gate does
# not trust a re-fetched checksum file.
ARCHIVE_SHA256 = {
    "oasdiff_1.33.0_darwin_all.tar.gz": "2a479337c15afdcbf0b1e89c0b4d0cf0176472dbc11483358fed1f831d1e46c5",  # noqa: E501
    "oasdiff_1.33.0_linux_amd64.tar.gz": "43a4e328e2d13ba1552d760aa68d2485c75c5621f309f6ff64ae895188345247",  # noqa: E501
    "oasdiff_1.33.0_linux_arm64.tar.gz": "4ae3c362d6074d919aada2dea82d0ee84366591600384455d0bdc658ddf8f7ae",  # noqa: E501
    "oasdiff_1.33.0_windows_amd64.tar.gz": "22f98c7247075f8a446e783595802d6d38637de1760df264f3d4b3309f766c5b",  # noqa: E501
    "oasdiff_1.33.0_windows_arm64.tar.gz": "d51bd1ea4b05ff9b314245d1e97f84c222b22ce34a930e8e305c68c32edbe951",  # noqa: E501
}


def _oasdiff_binary() -> Path:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(
        machine, "amd64"
    )
    if system == "darwin":
        asset = f"oasdiff_{OASDIFF_VERSION[1:]}_darwin_all.tar.gz"
    elif system == "windows":
        asset = f"oasdiff_{OASDIFF_VERSION[1:]}_windows_{arch}.tar.gz"
    else:
        asset = f"oasdiff_{OASDIFF_VERSION[1:]}_linux_{arch}.tar.gz"
    expected = ARCHIVE_SHA256.get(asset)
    if expected is None:
        sys.exit(f"[check-breaking] no recorded checksum for {asset}")
    dest = BIN_DIR / ("oasdiff.exe" if system == "windows" else "oasdiff")
    if dest.exists():
        return dest
    url = f"https://github.com/oasdiff/oasdiff/releases/download/{OASDIFF_VERSION}/{asset}"
    print(f"[check-breaking] downloading oasdiff {OASDIFF_VERSION} ...")
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    tmp_archive = BIN_DIR / asset
    urllib.request.urlretrieve(url, tmp_archive)
    digest = hashlib.sha256(tmp_archive.read_bytes()).hexdigest()
    if digest != expected:
        tmp_archive.unlink(missing_ok=True)
        sys.exit(f"[check-breaking] checksum mismatch for {asset}")
    with tarfile.open(tmp_archive) as bundle:
        names = {"oasdiff", "oasdiff.exe"}
        member = next(item for item in bundle.getmembers() if Path(item.name).name in names)
        payload = bundle.extractfile(member)
        if payload is None:
            sys.exit("[check-breaking] archive has no oasdiff binary")
        dest.write_bytes(payload.read())
    tmp_archive.unlink()
    dest.chmod(0o755)
    return dest


def _git_show_head_spec(tmp: Path) -> Path | None:
    r = subprocess.run(
        ["git", "show", f"HEAD:{SPEC.relative_to(ROOT).as_posix()}"],
        cwd=ROOT,
        capture_output=True,
    )
    if r.returncode != 0:
        return None  # new file or not a git repo — nothing to compare
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(r.stdout)
    return tmp


def main() -> int:
    if not shutil.which("git"):
        print("[check-breaking] no git — skipping")
        return 0
    base = _git_show_head_spec(ROOT / ".tools" / "openapi.base.yaml")
    if base is None:
        print("[check-breaking] no HEAD version — skipping")
        return 0
    binary = _oasdiff_binary()
    r = subprocess.run(
        [str(binary), "breaking", str(base), str(SPEC), "--format", "text"],
        capture_output=True,
        text=True,
    )
    # oasdiff exits 0 even with breaking changes; parse the summary line:
    # "N changes: X error, Y warning, Z info"
    import re

    output = r.stdout or r.stderr
    m = re.search(r"(\d+) changes: (\d+) error", output)
    breaking = bool(m and int(m.group(2)) > 0)
    if not breaking:
        print("[check-breaking] ok: no breaking changes vs HEAD")
        return 0
    print("[check-breaking] BREAKING CHANGES detected:")
    print(output)
    if os.environ.get("BREAKING_CHANGE_APPROVED") == "1":
        print("[check-breaking] approved via BREAKING_CHANGE_APPROVED=1")
        return 0
    print(
        "[check-breaking] FAIL: contract has breaking changes. "
        "If intentional, set BREAKING_CHANGE_APPROVED=1 and document "
        "with 'BREAKING:' in the commit message."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
