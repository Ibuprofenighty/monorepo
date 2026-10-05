"""Contract conformance: the RUNNING app must match contracts/http/openapi.yaml.

Contract-first means the implementation follows the hand-written source —
this test is the proof, on every run (blueprint 02 §8).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from fastapi.routing import APIRoute
from project_backend.bootstrap.app import create_app
from project_backend.platform.config.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]


def _load_spec() -> dict:
    return yaml.safe_load(
        (REPO_ROOT / "contracts" / "http" / "openapi.yaml").read_text(encoding="utf-8")
    )


def _canon(template: str) -> str:
    # /api/v1/resources/{resource_id} == /api/v1/resources/{id}
    return re.sub(r"\{[^}]+\}", "{}", template)


def _iter_api_routes(app) -> list[tuple[str, set[str]]]:
    """(path, methods) for every route, recursing into _IncludedRouter
    (newer FastAPI defers includes; prefix lives on the include context)."""
    out: list[tuple[str, set[str]]] = []

    def walk(routes, prefix: str = "") -> None:
        for r in routes:
            if isinstance(r, APIRoute):
                out.append((prefix + r.path, set(r.methods or [])))
            elif type(r).__name__ == "_IncludedRouter":
                ctx = r.include_context
                walk(r.original_router.routes, prefix + (ctx.prefix or ""))

    walk(app.routes)
    return out


def test_every_spec_path_is_implemented():
    spec = _load_spec()
    app = create_app(Settings())
    implemented = {
        (_canon(path), m.lower()) for path, methods in _iter_api_routes(app) for m in methods
    }
    missing = []
    for path, methods in spec["paths"].items():
        for method in methods:
            if method.lower() not in ("get", "post", "put", "patch", "delete", "head", "options"):
                continue
            if (_canon(path), method.lower()) not in implemented:
                missing.append(f"{method.upper()} {path}")
    assert not missing, f"spec paths not implemented: {missing}"


def test_no_undocumented_v1_routes():
    spec = _load_spec()
    spec_paths = {_canon(p) for p in spec["paths"]}
    app = create_app(Settings())
    undocumented = [
        f"{sorted(methods)} {path}"
        for path, methods in _iter_api_routes(app)
        if path.startswith("/api/v1") and _canon(path) not in spec_paths
    ]
    assert not undocumented, f"routes missing from contract: {undocumented}"


def test_error_codes_used_in_spec_exist_in_registry():
    """Every example code in the spec must be a registered public code."""
    import json

    spec_text = (REPO_ROOT / "contracts" / "http" / "openapi.yaml").read_text(encoding="utf-8")
    registry_codes: set[str] = set()
    for f in (REPO_ROOT / "contracts" / "errors").glob("*.yaml"):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        registry_codes.update(e["code"] for e in data["errors"])
    used = set(re.findall(r'"code":\s*"([A-Z][A-Z0-9_.]*)"', json.dumps(spec_text)))
    # also match yaml-style: code: XXX
    used.update(re.findall(r"code:\s*([A-Z][A-Z0-9_.]*)", spec_text))
    unknown = used - registry_codes
    assert not unknown, f"spec uses unregistered error codes: {unknown}"


def test_served_openapi_is_the_handwritten_source():
    """app.openapi() must return the hand-written file, not FastAPI inference."""
    app = create_app(Settings())
    served = app.openapi()
    source = _load_spec()
    assert served["info"]["title"] == source["info"]["title"]
    assert set(served["paths"]) == set(source["paths"])
