#!/usr/bin/env python3
"""New-project generator (the mother template's only job besides holding canonical code).

Reads a YAML answers file (see project-answers.example.yaml), validates it,
and creates ../<project_name> OUTSIDE this template with:

- only the selected clients + their required shared SDKs
- renamed Python package / TS scope / Dart package / compose project
- problem type namespace replaced
- mobile-flutter: android/ and ios/ created by the local Flutter SDK
  (`flutter create --org <mobile_org>`), template sources kept as-is
- pnpm-lock.yaml re-resolved for the selected JS workspace members
- contracts regenerated with the project's names
- renamed Python sources normalized with the project's own ruff rules
- instantiated docs/architecture/project-profile.md + canonical ADRs
- full docs/blueprint/ NOT copied (stays in the mother template)

Required tools on PATH: uv and pnpm (always), flutter (when mobile-flutter is selected).

Safety:
- target must not exist; never overwrites
- target must resolve outside the template dir (no path escape)
- on any failure the target is removed (no half-finished output)

Usage:
    ./create-project.sh --answers my-answers.yaml [--output-dir DIR]
    uv run --project apps/backend --frozen --extra dev python \\
        scripts/scaffold/create_project.py --answers my-answers.yaml   # Windows
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

_SCAFFOLD = Path(__file__).resolve().parent
if str(_SCAFFOLD) not in sys.path:
    sys.path.insert(0, str(_SCAFFOLD))
from selection import apply_selection, check_selection  # noqa: E402

try:
    import yaml
except ImportError:
    sys.exit("create_project.py requires pyyaml: pip install pyyaml")

TEMPLATE_ROOT = Path(__file__).resolve().parents[2]

CLIENT_DIRS = {
    "web-vite": "apps/web",
    "web-next": "apps/web-next",
    "wechat-native": "apps/miniprogram",
    "mobile-flutter": "apps/mobile",
}
TS_CLIENTS = {"web-vite", "web-next", "wechat-native"}

# Never copied into the new project.
SKIP_TOP = {
    "docs/blueprint",
    "examples",
    "scripts/scaffold",
    "apps/mobile/build",
    "packages/dart/api_client/pubspec.lock",
    "node_modules",
    ".venv",
    ".git",
}
SKIP_NAMES = {
    "node_modules",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".dart_tool",
    "dist",
    ".next",
    "out",
    "project-answers.example.yaml",
    "create-project.sh",
}

REQUIRED = ["project_name", "python_package", "ts_scope", "clients", "identity", "authz"]

# Files `flutter create` adds that the template does not use: the template's own
# lib/, test/ and pubspec.yaml are the app; only platform folders are adopted.
FLUTTER_KEEP_NEW = {"android", "ios", ".metadata", ".gitignore"}


def fail(msg: str) -> None:
    raise SystemExit(f"[create-project] ERROR: {msg}")


def tool(name: str) -> str:
    """Absolute path of a required executable (resolves Windows .cmd/.bat shims)."""
    path = shutil.which(name)
    if path is None:
        fail(f"required tool '{name}' not found on PATH")
    return path  # type: ignore[return-value]


def load_answers(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        fail(f"{path} must be a YAML mapping")
    return data


def validate(a: dict) -> dict:
    for key in REQUIRED:
        if not a.get(key):
            fail(f"missing required answer: {key} (🔴 blocking)")
    name = a["project_name"]
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        fail(f"project_name {name!r}: lowercase, hyphens, start with letter")
    pkg = a["python_package"]
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", pkg):
        fail(f"python_package {pkg!r}: valid python identifier, lowercase")
    scope = a["ts_scope"]
    if not re.fullmatch(r"[a-z0-9-]+", scope):
        fail(f"ts_scope {scope!r}: lowercase npm scope name")
    clients = a["clients"]
    if not isinstance(clients, list) or not clients:
        fail("clients: select at least one")
    unknown = [c for c in clients if c not in CLIENT_DIRS]
    if unknown:
        fail(f"unknown clients: {unknown} (choose from {sorted(CLIENT_DIRS)})")
    if "mobile-flutter" in clients and not a.get("dart_package"):
        fail("dart_package is required when mobile-flutter is selected (🔴 blocking)")
    if a.get("dart_package") and not re.fullmatch(r"[a-z_][a-z0-9_]*", a["dart_package"]):
        fail(f"dart_package {a['dart_package']!r}: valid dart package name")
    if "mobile-flutter" in clients:
        org = a.get("mobile_org")
        if not org:
            fail("mobile_org is required when mobile-flutter is selected (🔴 blocking)")
        if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", org):
            fail(f"mobile_org {org!r}: reverse domain, lowercase, e.g. com.example")
    tool("pnpm")
    tool("uv")
    if "web-next" in clients and a.get("web_rendering") not in (None, "ssr", "static-export"):
        fail("web_rendering must be ssr|static-export when web-next is selected")
    ns = a.get("problem_namespace", "https://api.example.com/problems")
    if not ns.startswith("https://"):
        fail("problem_namespace must be an https URL")
    a.setdefault("problem_namespace", ns)
    a.setdefault("git_init", True)
    a.setdefault("identity", "local")
    a.setdefault("authz", "local")
    a.setdefault("capabilities", [])
    check_selection(a)
    return a


def resolve_target(a: dict, override: str | None) -> Path:
    if override:
        target = Path(override)
    else:
        target = TEMPLATE_ROOT.parent / a["project_name"]
    target = target.resolve()
    troot = TEMPLATE_ROOT.resolve()
    if target == troot or troot in target.parents:
        fail(f"target {target} is inside the template — refusing")
    if target.exists():
        fail(f"target {target} already exists — refusing to overwrite")
    return target


def _skipped(rel: str) -> bool:
    """Top-level or nested skip paths (e.g. docs/blueprint)."""
    if rel in SKIP_TOP:
        return True
    return any(rel == s or rel.startswith(s + "/") for s in SKIP_TOP if "/" in s)


def copy_tree(target: Path, clients: list[str]) -> None:
    """Copy the template subset for the selected clients."""
    keep_dirs = {"apps/backend", "contracts"}
    for c in clients:
        keep_dirs.add(CLIENT_DIRS[c])
    if TS_CLIENTS & set(clients):
        keep_dirs.add("packages/ts/api-client")
    if "mobile-flutter" in clients:
        keep_dirs.add("packages/dart/api_client")

    def _copy(src: Path, dst_rel: str) -> None:
        if _skipped(dst_rel) or Path(dst_rel).name in SKIP_NAMES:
            return
        if src.is_dir():
            dst = target / dst_rel
            dst.mkdir(parents=True, exist_ok=True)
            for child in sorted(src.iterdir()):
                _copy(child, f"{dst_rel}/{child.name}")
        else:
            shutil.copy2(src, target / dst_rel)

    for item in sorted(TEMPLATE_ROOT.iterdir()):
        rel = item.relative_to(TEMPLATE_ROOT).as_posix()
        if rel == "apps":
            for app in sorted((TEMPLATE_ROOT / "apps").iterdir()):
                arel = f"apps/{app.name}"
                if arel in keep_dirs:
                    _copy(app, arel)
            continue
        if rel == "packages":
            # copy only the kept leaf packages (never the intermediate dirs alone)
            for leaf in ("packages/ts/api-client", "packages/dart/api_client"):
                if leaf in keep_dirs:
                    _copy(TEMPLATE_ROOT / leaf, leaf)
            continue
        _copy(item, rel)

    # prune dirs left empty by client selection (e.g. packages/dart/)
    for d in sorted((p for p in target.rglob("*") if p.is_dir()), reverse=True):
        try:
            if not any(d.iterdir()):
                d.rmdir()
        except OSError:
            pass


def replace_text(root: Path, replacements: list[tuple[str, str]], extensions: set[str]) -> int:
    """Literal text replacement across files whose suffix or exact name (e.g. Makefile)
    is in `extensions`. Returns files touched."""
    touched = 0
    for f in sorted(root.rglob("*")):
        if not f.is_file() or (f.suffix not in extensions and f.name not in extensions):
            continue
        if "node_modules" in f.parts or ".git" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = text
        for old, new_s in replacements:
            new = new.replace(old, new_s)
        if new != text:
            f.write_text(new, encoding="utf-8", newline="\n")
            touched += 1
    return touched


def rename_python_package(target: Path, pkg: str) -> None:
    src = target / "apps/backend/src/project_backend"
    dst = target / f"apps/backend/src/{pkg}"
    if not src.exists():
        fail("template broken: apps/backend/src/project_backend missing")
    src.rename(dst)
    exts = {
        ".py",
        ".toml",
        ".ini",
        ".cfg",
        ".txt",
        ".yaml",
        ".yml",
        ".md",
        ".sh",
        ".mjs",
        ".Dockerfile",
        ".importlinter",
        "Makefile",
    }
    n = replace_text(target, [("project_backend", pkg)], exts)
    print(f"[create-project] python package renamed in {n} files")
    # distribution name: project-backend -> <pkg with hyphens>
    dist_name = pkg.replace("_", "-")
    replace_text(
        target / "apps/backend",
        [
            ('"project-backend"', f'"{dist_name}"'),
            ("'project-backend'", f"'{dist_name}'"),
            ("project-backend", dist_name),
        ],
        {".toml", ".lock"},
    )
    # CI and the backend image reference the distribution name too
    for d in (".github", "infra/docker"):
        replace_text(
            target / d,
            [("--package project-backend", f"--package {dist_name}")],
            {".yaml", ".yml", ".Dockerfile"},
        )
    # isort first-party
    replace_text(target / "apps/backend", [('"project_backend"', f'"{pkg}"')], {".toml"})


def rename_ts_scope(target: Path, scope: str) -> None:
    n = replace_text(
        target,
        [("@project/", f"@{scope}/")],
        {".json", ".ts", ".tsx", ".mjs", ".md", ".yaml", ".yml", "Makefile"},
    )
    print(f"[create-project] TS scope renamed in {n} files")


def rename_dart(target: Path, dart_package: str, mobile_name: str) -> None:
    dart_dir = target / "packages/dart/api_client"
    repl = [("project_api_client", dart_package)]
    n = replace_text(dart_dir, repl, {".yaml", ".dart", ".md"})
    print(f"[create-project] dart api_client renamed in {n} files")
    n2 = replace_text(
        target / "apps/mobile",
        [("project_api_client", dart_package), ("project_mobile", mobile_name)],
        {".yaml", ".dart", ".md"},
    )
    print(f"[create-project] dart mobile app renamed in {n2} files")


def create_flutter_platforms(target: Path, org: str, mobile_name: str) -> None:
    """Add android/ and ios/ with the local Flutter SDK; existing files are never overwritten."""
    mob = target / "apps/mobile"
    before = {p.name for p in mob.iterdir()}
    print(f"[create-project] flutter create --org {org} (android, ios)")
    r = subprocess.run(
        [
            tool("flutter"),
            "create",
            "--org",
            org,
            "--project-name",
            mobile_name,
            "--platforms=android,ios",
            "--no-pub",
            ".",
        ],
        cwd=mob,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )
    if r.returncode != 0:
        print(r.stdout[-2000:], file=sys.stderr)
        print(r.stderr[-2000:], file=sys.stderr)
        fail("flutter create failed")
    for p in sorted(mob.iterdir()):
        if p.name in before or p.name in FLUTTER_KEEP_NEW:
            continue
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
    template_mobile = TEMPLATE_ROOT / "apps/mobile"
    for sub in ("lib", "test"):
        for p in sorted((mob / sub).rglob("*")):
            if p.is_file() and not (template_mobile / p.relative_to(mob)).exists():
                p.unlink()
    for platform in ("android", "ios"):
        if not (mob / platform).is_dir():
            fail(f"flutter create did not produce apps/mobile/{platform}")
    # flutter create emits platform line endings; the repo policy is LF (.gitattributes).
    for name in FLUTTER_KEEP_NEW - before:
        root = mob / name
        for p in [root] if root.is_file() else sorted(root.rglob("*")):
            if not p.is_file():
                continue
            data = p.read_bytes()
            if b"\r\n" in data and b"\0" not in data:
                p.write_bytes(data.replace(b"\r\n", b"\n"))
    # pub owns pubspec.lock: resolve it for the renamed packages before the initial commit.
    print("[create-project] flutter pub get (apps/mobile/pubspec.lock)")
    r = subprocess.run(
        [tool("flutter"), "pub", "get"],
        cwd=mob,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )
    if r.returncode != 0:
        print(r.stdout[-2000:], file=sys.stderr)
        print(r.stderr[-2000:], file=sys.stderr)
        fail("flutter pub get failed")


def install_js_workspace(target: Path) -> None:
    """Re-resolve pnpm-lock.yaml for the selected workspace members and install."""
    print("[create-project] pnpm install (lockfile for the selected workspace)")
    r = subprocess.run(
        [tool("pnpm"), "install", "--no-frozen-lockfile"],
        cwd=target,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1800,
    )
    if r.returncode != 0:
        print(r.stdout[-2000:], file=sys.stderr)
        print(r.stderr[-2000:], file=sys.stderr)
        fail("pnpm install failed")


def apply_project_naming(target: Path, a: dict) -> None:
    name = a["project_name"]
    repl: list[tuple[str, str]] = [
        ("COMPOSE_PROJECT_NAME=project", f"COMPOSE_PROJECT_NAME={name}"),
        ("name: project\n", f"name: {name}\n"),  # compose project name
        ('"project-template"', f'"{name}"'),
        ("project-test", f"{name}-test"),
    ]
    n = replace_text(target, repl, {".yaml", ".yml", ".json", ".env.example", ".sh", ".md"})
    print(f"[create-project] project naming applied in {n} files")
    # pnpm workspace: keep only selected clients
    ws = target / "pnpm-workspace.yaml"
    lines = ["packages:"]
    for c in a["clients"]:
        if c in ("web-vite", "web-next", "wechat-native"):
            lines.append(f'  - "apps/{CLIENT_DIRS[c].split("/")[1]}"')
    if TS_CLIENTS & set(a["clients"]):
        lines.append('  - "packages/ts/*"')
    ws.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    # problem namespace
    ns_old = "https://api.example.com/problems"
    ns_new = a["problem_namespace"].rstrip("/")
    n2 = replace_text(target / "contracts", [(ns_old, ns_new)], {".yaml"})
    print(f"[create-project] problem namespace replaced in {n2} files")
    # uv.lock workspace member names
    replace_text(
        target, [('"project-backend"', f'"{a["python_package"].replace("_", "-")}"')], {".lock"}
    )


def apply_web_rendering(target: Path, a: dict) -> None:
    """Apply web_rendering (ssr|static-export) to next.config.ts + web.Dockerfile defaults."""
    dockerfile = target / "infra/docker/web.Dockerfile"
    compose = target / "infra/compose/compose.yaml"

    def patch_compose(app: str, output: str) -> None:
        text = compose.read_text(encoding="utf-8")
        text = text.replace("APP: ${WEB_APP:-web}", f"APP: ${{WEB_APP:-{app}}}")
        text = text.replace(
            "WEB_OUTPUT: ${WEB_OUTPUT:-dist}", f"WEB_OUTPUT: ${{WEB_OUTPUT:-{output}}}"
        )
        compose.write_text(text, encoding="utf-8", newline="\n")

    def patch_dockerfile(app: str, output: str) -> None:
        df = dockerfile.read_text(encoding="utf-8")
        df = df.replace(
            "ARG APP=web\nARG WEB_OUTPUT=dist", f"ARG APP={app}\nARG WEB_OUTPUT={output}"
        )
        dockerfile.write_text(df, encoding="utf-8", newline="\n")

    if "web-next" in a["clients"]:
        mode = a.get("web_rendering") or "static-export"
        cfg = target / "apps/web-next/next.config.ts"
        text = cfg.read_text(encoding="utf-8")
        if mode == "ssr":
            text = text.replace('output: "export",', 'output: "standalone",')
            text = text.replace(
                "// Static export by default; switch to SSR per project-profile §7.",
                "// SSR via standalone output (set by generator: web_rendering=ssr).",
            )
            patch_dockerfile("web-next", "server")
            patch_compose("web-next", "server")
            # SSR: node serves :3000 directly and calls the API over the compose network.
            text_c = compose.read_text(encoding="utf-8")
            text_c = text_c.replace("target: runtime-static", "target: runtime-server").replace(
                '    ports:\n      - "${NGINX_PORT:-8080}:80"',
                "    environment:\n      INTERNAL_API_URL: http://api:8000\n"
                '    ports:\n      - "${WEB_PORT:-3000}:3000"',
            )
            compose.write_text(text_c, encoding="utf-8", newline="\n")
        else:
            patch_dockerfile("web-next", "out")
            patch_compose("web-next", "out")
        cfg.write_text(text, encoding="utf-8", newline="\n")
        print(f"[create-project] web-next rendering mode: {mode}")
    elif "web-vite" in a["clients"]:
        # Dockerfile/compose defaults already APP=web / WEB_OUTPUT=dist
        print("[create-project] web client: vite (dist)")


def _drop_verify_token(text: str, token: str) -> str:
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("verify:"):
            newline = "\n" if line.endswith("\n") else ""
            raw = line.rstrip("\r\n")
            comment = ""
            if "##" in raw:
                raw, comment = raw.split("##", 1)
                comment = "##" + comment
            words = [word for word in raw.split() if word != token]
            raw = " ".join(words)
            if comment:
                raw = f"{raw} {comment}"
            line = raw + newline
        lines.append(line)
    return "".join(lines)


def prune_ci(target: Path, a: dict) -> None:
    """Drop CI jobs that belong to clients the generator did not copy.

    Per-client build lines and the Dart target are removed by selection markers.
    A project with no TypeScript client also drops the web job and its verify tokens.
    """
    ci_path = target / ".github/workflows/ci.yaml"
    if not ci_path.exists():
        return
    text = ci_path.read_text(encoding="utf-8")
    make_path = target / "Makefile"
    make = make_path.read_text(encoding="utf-8") if make_path.exists() else ""
    if "mobile-flutter" not in a["clients"]:
        text = re.sub(r"\n  dart:\n(?:    .*\n)+?(?=\n  \w)", "\n", text)
        make = _drop_verify_token(make, "check-dart")
    if not (TS_CLIENTS & set(a["clients"])):
        text = re.sub(r"\n  web:\n(?:    .*\n)+?(?=\n  \w)", "\n", text)
        for token in ("lint-ts", "typecheck-ts", "test-unit-ts", "build-clients"):
            make = _drop_verify_token(make, token)
    ci_path.write_text(text, encoding="utf-8", newline="\n")
    if make_path.exists():
        make_path.write_text(make, encoding="utf-8", newline="\n")
    print("[create-project] CI pruned to selected clients")


def write_project_profile(target: Path, a: dict) -> None:
    tpl = (target / "docs/architecture/project-profile.md").read_text(encoding="utf-8")
    clients = ", ".join(a["clients"])
    app_dirs = ", ".join(CLIENT_DIRS[c] for c in a["clients"])
    mobile = "mobile-flutter" in a["clients"]
    subs = {
        "{{project_name}}": a["project_name"],
        "{{python_package}}": a["python_package"],
        "{{ts_scope}}": a["ts_scope"],
        "{{dart_package}}": a.get("dart_package", "n/a") if mobile else "n/a",
        "{{mobile_org}}": a["mobile_org"] if mobile else "n/a",
        "{{product_goal}}": a.get("product_goal", "待确定"),
        "{{clients}}": clients,
        "{{app_dirs}}": app_dirs,
        "{{rendering}}": a.get("web_rendering", "n/a") if "web-next" in a["clients"] else "n/a",
        "{{out_of_scope}}": a.get("out_of_scope", "待确定"),
        "{{modules}}": ", ".join(a.get("modules", ["catalog"])),
        "{{data_ownership}}": a.get("data_ownership", "待确定"),
        "{{legacy_data}}": a.get("legacy_data", "无"),
        "{{identity}}": a["identity"],
        "{{session}}": a.get("session", "待确定"),
        "{{secrets}}": a.get("secrets", "环境变量 / secret manager 注入"),
        "{{dev_env}}": a.get("dev_env", "待确定"),
        "{{topology}}": a.get("deploy_target", "compose") + " + nginx",
        "{{slo}}": a.get("slo", "待确定"),
        "{{open_items}}": a.get("open_items", "无"),
    }
    for old, new_s in subs.items():
        tpl = tpl.replace(old, new_s)
    # strip the template's instructional footer (it told the filler to delete this line)
    tpl = tpl.split("\n---\n")[0].rstrip() + "\n"
    (target / "docs/architecture/project-profile.md").write_text(
        tpl, encoding="utf-8", newline="\n"
    )
    print("[create-project] docs/architecture/project-profile.md instantiated")


def write_project_readme(target: Path, a: dict) -> None:
    clients = "\n".join(f"- {CLIENT_DIRS[c]}" for c in a["clients"])
    readme = f"""# {a["project_name"]}

{a.get("product_goal", "")}

由 monorepo 工程母版生成（`create-project.sh`）。母版规范见生成时的
`docs/blueprint/`（未复制到本仓库）；实例化后的架构选择见
`docs/architecture/project-profile.md`。

## 客户端

{clients}

## 常用命令

```bash
make bootstrap   # 检查工具链
make dev         # 启动开发拓扑
make verify      # 全部门禁
make generate    # 契约变更后重新生成
```

## 纪律

- `contracts/` 是唯一手工契约源；`*/generated/` 永不手改
- 后端授权唯一权威在服务端；前端不做最终裁决
- 没有真实执行不写 PASS
"""
    (target / "README.md").write_text(readme, encoding="utf-8", newline="\n")


def regenerate_contracts(target: Path) -> None:
    """Re-run codegen in the new project (namespace/package renames change output)."""
    print("[create-project] regenerating contracts in new project")
    r = subprocess.run(
        [sys.executable, "scripts/contracts/generate.py"],
        cwd=target,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    if r.returncode != 0:
        print(r.stdout[-2000:], file=sys.stderr)
        print(r.stderr[-2000:], file=sys.stderr)
        fail("contract regeneration failed — is the toolchain installed? (make bootstrap)")


def reset_validation_evidence(target: Path) -> None:
    """The template's own audit records do not describe the new project."""
    path = target / "docs/audits/validation-evidence.md"
    head, marker, _ = path.read_text(encoding="utf-8").partition("\n## 记录\n")
    if not marker:
        fail("template broken: docs/audits/validation-evidence.md lacks '## 记录'")
    path.write_text(head + marker + "\n（按时间倒序追加）\n", encoding="utf-8", newline="\n")


def normalize_python(target: Path) -> None:
    """Renamed packages change import order and line lengths; re-apply the project's
    own ruff rules so the new project passes `make lint` as generated."""
    print("[create-project] ruff fix + format (renamed Python sources)")
    uv = tool("uv")
    base = [uv, "run", "--frozen", "--extra", "dev", "ruff"]
    paths = ["src", "tests", "../../scripts"]
    for args in (["check", "--fix", "--exit-zero", *paths], ["format", *paths], ["check", *paths]):
        r = subprocess.run(
            [*base, *args],
            cwd=target / "apps/backend",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
        )
        if r.returncode != 0:
            print(r.stdout[-3000:], file=sys.stderr)
            print(r.stderr[-2000:], file=sys.stderr)
            fail(f"ruff {args[0]} failed in the new project")


def git_init(target: Path, a: dict) -> None:
    if not a.get("git_init", True):
        print("[create-project] git_init=false, skipping")
        return
    if not shutil.which("git"):
        print("[create-project] warning: git not found, skipping git init")
        return
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    subprocess.run(["git", "add", "-A"], cwd=target, check=True)
    owner = a.get("owner", "template")
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=template",
            "-c",
            "user.email=template@localhost",
            "commit",
            "-qm",
            f"initial project from template (owner: {owner})",
        ],
        cwd=target,
        check=True,
    )
    print("[create-project] git initialized with initial commit")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", required=True, help="YAML answers file")
    ap.add_argument("--output-dir", default=None, help="override target dir")
    args = ap.parse_args()

    answers_path = Path(args.answers)
    if not answers_path.exists():
        fail(f"answers file not found: {answers_path}")
    a = validate(load_answers(answers_path))
    target = resolve_target(a, args.output_dir)
    print(f"[create-project] template: {TEMPLATE_ROOT}")
    print(f"[create-project] target:   {target}")
    print(f"[create-project] clients:   {', '.join(a['clients'])}")

    try:
        target.mkdir(parents=True)
        copy_tree(target, a["clients"])
        rename_python_package(target, a["python_package"])
        apply_selection(target, a)
        rename_ts_scope(target, a["ts_scope"])
        mobile_name = a["project_name"].replace("-", "_") + "_mobile"
        if "mobile-flutter" in a["clients"]:
            rename_dart(target, a["dart_package"], mobile_name)
        apply_project_naming(target, a)
        apply_web_rendering(target, a)
        prune_ci(target, a)
        if "mobile-flutter" in a["clients"]:
            create_flutter_platforms(target, a["mobile_org"], mobile_name)
        install_js_workspace(target)
        regenerate_contracts(target)
        normalize_python(target)
        write_project_profile(target, a)
        write_project_readme(target, a)
        reset_validation_evidence(target)
        git_init(target, a)
    except BaseException:
        # BaseException (not Exception): fail() raises SystemExit, and Ctrl+C
        # (KeyboardInterrupt) must also not leave a half-finished project behind.
        print(f"[create-project] FAILED — removing incomplete {target}", file=sys.stderr)
        shutil.rmtree(target, ignore_errors=True)
        raise

    print(f"[create-project] done: {target}")
    print(f"[create-project] next: cd {target} && make bootstrap && make dev")
    return 0


if __name__ == "__main__":
    sys.exit(main())
