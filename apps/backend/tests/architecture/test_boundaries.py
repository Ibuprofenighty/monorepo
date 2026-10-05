"""Architecture boundary tests (blueprint 01 §8, 04 §3).

AST-based, dependency-free: parses imports and FAILS on violations.
This is the executable version of tooling/architecture/backend.importlinter.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[3] / "src" / "project_backend"

FORBIDDEN_IN_DOMAIN = {"sqlalchemy", "fastapi", "pydantic_settings", "redis", "httpx", "arq"}
FORBIDDEN_IN_APPLICATION = {"sqlalchemy", "fastapi", "redis", "arq"}


def _imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    return mods


def _module_of(path: Path) -> str | None:
    """e.g. .../modules/catalog/domain/x.py -> catalog ; None if outside modules/."""
    parts = path.relative_to(SRC).parts
    if len(parts) > 2 and parts[0] == "modules":
        return parts[1]
    return None


def test_domain_has_no_tech_imports():
    violations = []
    for f in (SRC / "modules").rglob("domain/*.py"):
        bad = _imports_of(f) & FORBIDDEN_IN_DOMAIN
        if bad:
            violations.append(f"{f.relative_to(SRC)}: {sorted(bad)}")
    assert not violations, f"domain layer tech imports: {violations}"


def test_application_has_no_infra_imports():
    violations = []
    for f in (SRC / "modules").rglob("application/**/*.py"):
        bad = _imports_of(f) & FORBIDDEN_IN_APPLICATION
        if bad:
            violations.append(f"{f.relative_to(SRC)}: {sorted(bad)}")
    assert not violations, f"application layer infra imports: {violations}"


def test_cross_module_only_via_public():
    """modules/X may import modules/Y only through Y.public (blueprint 04 §3)."""
    violations = []
    for f in (SRC / "modules").rglob("*.py"):
        mod = _module_of(f)
        if mod is None:
            continue
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                parts = node.module.split(".")
                if (
                    len(parts) >= 3
                    and parts[0] == "project_backend"
                    and parts[1] == "modules"
                    and parts[2] != mod
                ):
                    rest = parts[3:]
                    if not rest or rest[0] != "public":
                        violations.append(f"{f.relative_to(SRC)} imports {node.module}")
    assert not violations, f"cross-module private imports: {violations}"


def test_platform_does_not_import_modules():
    violations = []
    for f in (SRC / "platform").rglob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module]
            for m in mods:
                if m.startswith("project_backend.modules"):
                    violations.append(f"{f.relative_to(SRC)} imports {m}")
    assert not violations, f"platform imports business modules: {violations}"
