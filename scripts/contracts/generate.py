#!/usr/bin/env python3
"""Contract codegen — the ONLY way generated/ is produced (blueprint 02 §2, §8).

Sources (hand-written, single source of truth):
  contracts/errors/*.yaml        → error registries
  contracts/http/openapi.yaml    → HTTP contract

Outputs (committed, NEVER hand-edited):
  packages/ts/api-client/src/generated/errors.ts
  packages/ts/api-client/src/generated/schema.ts      (via openapi-typescript)
  apps/backend/src/project_backend/generated/http/errors.py
  apps/backend/src/project_backend/generated/http/models.py  (via datamodel-code-generator)
  packages/dart/api_client/lib/src/generated/errors.dart
  packages/dart/api_client/lib/src/generated/models.dart     (built in)

Strictness rule: --check regenerates EVERYTHING (including the external
openapi-typescript and datamodel-code-generator runs) into a clean temp dir
and diffs the complete file set. Committed generated files are never copied
into the temp dir — that would hide drift.

Usage:
  python scripts/contracts/generate.py              # regenerate in place
  python scripts/contracts/generate.py --check      # strict drift check
  python scripts/contracts/generate.py --check --quiet
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("generate.py requires pyyaml: pip install pyyaml")

_CONTRACTS = Path(__file__).resolve().parent
if str(_CONTRACTS) not in sys.path:
    sys.path.insert(0, str(_CONTRACTS))
from dart_subset import DartSubsetError, render_models  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ERRORS_DIR = ROOT / "contracts" / "errors"
OPENAPI = ROOT / "contracts" / "http" / "openapi.yaml"


def _backend_gen_dir() -> Path:
    """Generated dir under apps/backend/src/<package>/generated/http.

    Discovered, not hardcoded — the package is renamed per project by
    scripts/scaffold/create_project.py.
    """
    candidates = list((ROOT / "apps" / "backend" / "src").glob("*/generated/http"))
    assert len(candidates) == 1, f"expected one generated/http dir, found: {candidates}"
    return Path("apps/backend/src") / candidates[0].relative_to(ROOT / "apps" / "backend" / "src")


TS_GEN = Path("packages/ts/api-client/src/generated")
PY_GEN = _backend_gen_dir()
DART_GEN = Path("packages/dart/api_client/lib/src/generated")

# Pinned codegen tool versions (blueprint 09 §7: codegen 工具版本锁).
# openapi-typescript is pinned in the root package.json and pnpm-lock.yaml.
CODEGEN_VERSIONS = {
    "datamodel-code-generator": "0.83.0",
}

QUIET = False


def log(*args: object) -> None:
    if not QUIET:
        print(*args)


def load_registry() -> list[dict]:
    errors: list[dict] = []
    for f in sorted(ERRORS_DIR.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert data.get("schema_version") == 1, f"unsupported schema_version in {f}"
        seen = set()
        for e in data["errors"]:
            for key in ("code", "type", "http_status", "title"):
                assert key in e, f"{f}: error missing {key}: {e}"
            assert e["code"] not in seen, f"{f}: duplicate code {e['code']}"
            seen.add(e["code"])
            errors.append(e)
    codes = [e["code"] for e in errors]
    assert len(codes) == len(set(codes)), "duplicate error code across registry files"
    return errors


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def gen_ts_errors(errors: list[dict], out: Path) -> None:
    lines = [
        "// AUTO-GENERATED from contracts/errors/*.yaml — do not edit.",
        "// Regenerate: make generate",
        "",
        "export const ErrorCodes = {",
    ]
    for e in errors:
        lines.append(f'  "{e["code"]}": {e["http_status"]},')
    lines += [
        "} as const;",
        "",
        "export type ErrorCode = keyof typeof ErrorCodes;",
        "",
        "export const ErrorTypes: Record<ErrorCode, string> = {",
    ]
    for e in errors:
        lines.append(f'  "{e["code"]}": "{e["type"]}",')
    lines += ["};", ""]
    write_text(out / TS_GEN / "errors.ts", "\n".join(lines))


def gen_py_errors(errors: list[dict], out: Path) -> None:
    lines = [
        '"""AUTO-GENERATED from contracts/errors/*.yaml — do not edit."""',
        "",
        "from __future__ import annotations",
        "",
        "",
        "class ErrorCode:",
        '    """Stable public error codes. Use these, never string literals."""',
        "",
    ]
    for e in errors:
        lines.append(f'    {e["code"].replace(".", "_")} = "{e["code"]}"')
    lines += [
        "",
        "",
        "ERROR_HTTP_STATUS: dict[str, int] = {",
    ]
    for e in errors:
        lines.append(f"    ErrorCode.{e['code'].replace('.', '_')}: {e['http_status']},")
    lines += ["}", "", "", "ERROR_TYPES: dict[str, str] = {"]
    for e in errors:
        lines.append(f'    ErrorCode.{e["code"].replace(".", "_")}: "{e["type"]}",')
    lines += ["}", "", "", "ERROR_TITLES: dict[str, str] = {"]
    for e in errors:
        title = e["title"].replace('"', '\\"')
        lines.append(f'    ErrorCode.{e["code"].replace(".", "_")}: "{title}",')
    lines += ["}", ""]
    write_text(out / PY_GEN / "errors.py", "\n".join(lines))


def gen_dart_errors(errors: list[dict], out: Path) -> None:
    lines = [
        "// AUTO-GENERATED from contracts/errors/*.yaml — do not edit.",
        "// Constant names mirror the registry codes shared with TS/Python.",
        "// ignore_for_file: constant_identifier_names",
        "",
        "/// Stable public error codes.",
        "abstract final class ErrorCodes {",
    ]
    for e in errors:
        const = e["code"].replace(".", "_").upper()
        lines.append(f'  static const String {const} = "{e["code"]}";')
    lines += ["}", ""]
    write_text(out / DART_GEN / "errors.dart", "\n".join(lines))


def gen_dart_models(openapi: dict, out: Path) -> None:
    """Deterministic Dart wire models. Fails on schemas outside the Dart subset.

    Problem is excluded: problem.dart has a hand-written parser, and its uri
    formats are outside the subset.
    """
    try:
        text = render_models(openapi)
    except DartSubsetError as exc:
        sys.exit(f"generate.py: Dart subset: {exc}")
    write_text(out / DART_GEN / "models.dart", text)


def tool(name: str) -> str:
    """Absolute path of a required executable (resolves Windows .cmd/.exe shims)."""
    path = shutil.which(name)
    if path is None:
        sys.exit(f"generate.py: required tool '{name}' not found on PATH (run: make bootstrap)")
    return path


def run(cmd: list[str], cwd: Path) -> None:
    log("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=QUIET)


def gen_ts_schema(out: Path) -> None:
    """openapi-typescript is a pinned root devDependency (package.json + pnpm-lock.yaml)."""
    run(
        [
            tool("pnpm"),
            "exec",
            "openapi-typescript",
            str(OPENAPI),
            "-o",
            str(out / TS_GEN / "schema.ts"),
        ],
        cwd=ROOT,
    )


def gen_py_models(out: Path) -> None:
    """Captured from stdout and written by write_text: the tool's own file
    writer uses the platform line ending, which would make Windows output drift."""
    cmd = [
        tool("uvx"),
        "--from",
        # The black/isort extras back the --formatters below.
        "datamodel-code-generator[black,isort]==" + CODEGEN_VERSIONS["datamodel-code-generator"],
        "datamodel-codegen",
        "--input",
        str(OPENAPI),
        "--input-file-type",
        "openapi",
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--use-annotated",
        "--snake-case-field",
        "--field-constraints",
        "--disable-timestamp",
        "--formatters",
        "black",
        "isort",
    ]
    log("+", " ".join(cmd))
    r = subprocess.run(
        cmd,
        cwd=ROOT,
        check=True,
        capture_output=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if not QUIET:
        sys.stderr.write(r.stderr.decode("utf-8", errors="replace"))
    write_text(out / PY_GEN / "models.py", r.stdout.decode("utf-8").replace("\r\n", "\n"))


def generate(out: Path) -> None:
    """Regenerate the complete generated file set under `out`.

    `out` is either ROOT (in place) or a temp dir (--check). All generators
    run in both modes — no exceptions, no committed-file copying.
    The Dart package is skipped when not present (projects without
    mobile-flutter don't have it).
    """
    errors = load_registry()
    log(f"registry: {len(errors)} public error codes")
    gen_ts_errors(errors, out)
    gen_py_errors(errors, out)
    if (ROOT / "packages" / "dart" / "api_client").exists():
        gen_dart_errors(errors, out)
        openapi = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
        gen_dart_models(openapi, out)
    else:
        log("dart package not present — skipping dart codegen")
    gen_ts_schema(out)
    gen_py_models(out)


def _is_hand_written(path: Path) -> bool:
    # Package markers are hand-written, not generated — never diff them.
    return path.name == "__init__.py"


def _is_cache(path: Path) -> bool:
    # Bytecode caches and similar byproducts are not generated sources.
    return "__pycache__" in path.parts or path.name.endswith((".pyc", ".pyo"))


def diff_trees(fresh: Path, committed: Path) -> list[str]:
    diffs: list[str] = []
    subdirs = [TS_GEN, PY_GEN]
    if (committed / DART_GEN).exists() or (fresh / DART_GEN).exists():
        subdirs.append(DART_GEN)
    for sub in subdirs:
        for f in sorted((fresh / sub).rglob("*")):
            if f.is_dir() or _is_hand_written(f) or _is_cache(f):
                continue
            rp = f.relative_to(fresh / sub)
            other = committed / sub / rp
            if not other.exists():
                diffs.append(f"+ {sub}/{rp} (generated file missing from repo)")
            elif f.read_bytes() != other.read_bytes():
                diffs.append(f"M {sub}/{rp}")
        for f in sorted((committed / sub).rglob("*")):
            if f.is_dir() or _is_hand_written(f) or _is_cache(f):
                continue
            rp = f.relative_to(committed / sub)
            if not (fresh / sub / rp).exists():
                diffs.append(f"- {sub}/{rp} (stale file not produced by generators)")
    return diffs


def main() -> int:
    global QUIET
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="regenerate to temp dir and diff")
    ap.add_argument("--quiet", action="store_true", help="minimal output (for doctor.py)")
    args = ap.parse_args()
    QUIET = args.quiet

    if not args.check:
        generate(ROOT)
        log("done. Review the diff, then commit.")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        generate(Path(tmp))
        diffs = diff_trees(Path(tmp), ROOT)
    if diffs:
        print("GENERATED DRIFT DETECTED:")
        for d in diffs:
            print(" ", d)
        print("Run: make generate")
        return 1
    if not QUIET:
        print("check-generated: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
