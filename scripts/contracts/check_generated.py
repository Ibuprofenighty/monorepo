#!/usr/bin/env python3
"""make check-generated — thin wrapper so the Makefile target is explicit."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.exit(
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/contracts/generate.py"), "--check"]
    ).returncode
)
