#!/usr/bin/env python3
"""Spec traceability (blueprint 10 §3): every spec scenario has a test, every
test's spec reference exists.

Convention:
- specs/<area>/<name>.yaml carry `id:` (e.g. CATALOG.DELETE.LOCKED_NO_EFFECT)
  and each scenario lists `tests:` with pytest node ids or file paths.
- Tests reference spec ids in a `# spec: <ID>` comment or `spec:` marker.

Checks:
1. Every spec id is unique.
2. Every scenario's listed test target exists on disk.
3. Every `# spec: <ID>` in tests/ and apps/ points at a known spec id.

Exit 1 on any violation. Usage: python scripts/quality/check_traceability.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("check_traceability.py requires pyyaml")

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
SPEC_REF_RE = re.compile(r"#\s*spec:\s*([A-Z0-9._-]+)")


def _defined_test_functions(path: Path) -> set[str]:
    """Test function/class names defined in a file (AST, not text search)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names.add(f"{node.name}::{item.name}")
                    names.add(item.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names


def load_specs() -> tuple[dict[str, Path], list[str]]:
    ids: dict[str, Path] = {}
    errors: list[str] = []
    for f in sorted(SPECS.rglob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for sc in data.get("scenarios", []):
            sid = sc.get("id")
            if not sid:
                errors.append(f"{f.relative_to(ROOT)}: scenario without id")
                continue
            if sid in ids:
                other = ids[sid].relative_to(ROOT)
                errors.append(f"duplicate spec id {sid} ({f.relative_to(ROOT)} and {other})")
            ids[sid] = f
            for t in sc.get("tests", []):
                node = t.split("::")[0]
                target = ROOT / node
                if not target.exists():
                    errors.append(f"{sid}: listed test target missing: {t}")
                    continue
                if "::" in t:
                    # AST check: the function must actually be defined, not just
                    # the file existing (catches renames/deletions).
                    func = t.split("::", 1)[1]
                    if func not in _defined_test_functions(target):
                        errors.append(f"{sid}: listed test function not defined: {t}")
    return ids, errors


def main() -> int:
    errors: list[str] = []
    if not SPECS.exists():
        print("check-traceability: no specs/ directory — nothing to check")
        return 0
    ids, errors = load_specs()

    for base in ("apps", "packages", "tests"):
        for f in (ROOT / base).rglob("*.py"):
            if "__pycache__" in f.parts:
                continue
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                m = SPEC_REF_RE.search(line)
                if m and m.group(1) not in ids:
                    errors.append(f"{f.relative_to(ROOT)}:{i}: unknown spec id {m.group(1)}")
    # TS side: // spec: <ID>
    ts_ref = re.compile(r"//\s*spec:\s*([A-Z0-9._-]+)")
    for base in ("apps", "packages"):
        for f in (ROOT / base).rglob("*.ts"):
            if "node_modules" in f.parts or ".test." in f.name:
                continue
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                m = ts_ref.search(line)
                if m and m.group(1) not in ids:
                    errors.append(f"{f.relative_to(ROOT)}:{i}: unknown spec id {m.group(1)}")

    if errors:
        print("TRACEABILITY FAILURES:")
        for e in errors:
            print(" ", e)
        return 1
    print(f"check-traceability: ok ({len(ids)} spec ids)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
