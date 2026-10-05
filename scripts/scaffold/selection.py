"""Generate-time identity and capability pruning (ADR 0006).

The mother template keeps every adapter, the redis/worker capability, and uv.lock.
This module runs only on a copied project: it keeps one verifier, deletes the
others, removes marked blocks for capabilities that were not selected, drops
unused redis/arq dependencies, and rewrites that project's lock.
storage and llm have no canonical implementation and fail the generator.
Cloud verifiers are future modules under platform/authn/verifiers/; they are
not accepted answers yet.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

IDENTITIES = ("local", "wechat", "keycloak")
CAPABILITIES = ("redis", "worker", "storage", "llm")
UNIMPLEMENTED_CAPABILITIES = frozenset({"storage", "llm"})

_TEST_FILES = {
    "local": "test_authn_verifier.py",
    "wechat": "test_wechat_verifier.py",
    "keycloak": "test_keycloak_verifier.py",
}

_BEGIN = re.compile(r"^([ \t]*)# begin ([a-z0-9:-]+)\s*$")
_END = re.compile(r"^([ \t]*)# end ([a-z0-9:-]+)\s*$")
_IDENTITY_REGION = re.compile(
    r"(^[ \t]*# begin identity\n)(.*?)(^[ \t]*# end identity\n)",
    re.M | re.S,
)

_COMPOSE_ENV = {
    "wechat": (
        "WECHAT_APP_ID: ${WECHAT_APP_ID:?set WECHAT_APP_ID}",
        "WECHAT_APP_SECRET: ${WECHAT_APP_SECRET:?set WECHAT_APP_SECRET}",
    ),
    "keycloak": (
        "KEYCLOAK_ISSUER: ${KEYCLOAK_ISSUER:?set KEYCLOAK_ISSUER}",
        "KEYCLOAK_AUDIENCE: ${KEYCLOAK_AUDIENCE:?set KEYCLOAK_AUDIENCE}",
    ),
}
_FILE_ENV = {
    "wechat": ("WECHAT_APP_ID=", "WECHAT_APP_SECRET="),
    "keycloak": (
        "KEYCLOAK_ISSUER=https://keycloak.example/realms/project",
        "KEYCLOAK_AUDIENCE=project-api",
    ),
}

_WECHAT_IMPORT = """from {pkg}.platform.authn.verifiers.wechat import (
    DEV_WECHAT_APP_ID,
    DEV_WECHAT_APP_SECRET,
    validate_identity_settings,
)
"""
_KEYCLOAK_IMPORT = """from {pkg}.platform.authn.verifiers.keycloak import (
    DEV_KEYCLOAK_AUDIENCE,
    DEV_KEYCLOAK_ISSUER,
    validate_identity_settings,
)
"""

_WECHAT_BLOCK = """    wechat_app_id: str = DEV_WECHAT_APP_ID
    wechat_app_secret: SecretStr = SecretStr(DEV_WECHAT_APP_SECRET)
    jwt_secret: SecretStr = SecretStr(DEV_JWT_SECRET)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "project-api"
    jwt_audience: str = "project-clients"
    access_token_expire_minutes: int = 120

    @model_validator(mode="after")
    def _deployed_env_requires_real_secret(self) -> "Settings":
        validate_identity_settings(self)
        if self.app_env in DEPLOYED_ENVS:
            secret = self.jwt_secret.get_secret_value()
            if secret == DEV_JWT_SECRET:
                raise ValueError(f"JWT_SECRET must be injected when APP_ENV={self.app_env}")
            if len(secret.encode("utf-8")) < MIN_JWT_SECRET_BYTES:
                raise ValueError(f"JWT_SECRET must be at least {MIN_JWT_SECRET_BYTES} bytes")
        return self
"""

_KEYCLOAK_BLOCK = """    keycloak_issuer: str = DEV_KEYCLOAK_ISSUER
    keycloak_audience: str = DEV_KEYCLOAK_AUDIENCE

    @model_validator(mode="after")
    def _deployed_env_requires_real_secret(self) -> "Settings":
        validate_identity_settings(self)
        return self
"""

_WECHAT_TAG = """  - name: auth
    description: Session establishment for the selected identity
"""

_WECHAT_PATH = """
  /api/v1/session/wechat:
    post:
      operationId: createWechatSession
      tags: [auth]
      summary: Exchange a wx.login code for an application session
      description: >-
        The server calls WeChat code2session. session_key and the app secret
        never leave the server. The response is an application bearer token.
      security: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [code]
              additionalProperties: false
              properties:
                code: { type: string, minLength: 1 }
      responses:
        "200":
          description: Application session
          content:
            application/json:
              schema:
                type: object
                required: [access_token, token_type, expires_in]
                additionalProperties: false
                properties:
                  access_token: { type: string }
                  token_type: { type: string, enum: [Bearer] }
                  expires_in: { type: integer, minimum: 1 }
        "401": { $ref: "#/components/responses/AuthnRequired" }
        "500": { $ref: "#/components/responses/Internal" }

"""


def fail(msg: str) -> None:
    raise SystemExit(f"[create-project] ERROR: {msg}")


def check_selection(answers: dict) -> None:
    identity = answers.get("identity") or "local"
    if identity not in IDENTITIES:
        fail(
            f"identity {identity!r} is not implemented "
            f"(choose from {list(IDENTITIES)}). Cloud verifiers such as aws, gcp, "
            "azure, and alibaba are not selectable until a module exists"
        )
    clients = answers.get("clients") or []
    if "wechat-native" in clients and identity != "wechat":
        fail("wechat-native requires identity: wechat")
    caps = answers.get("capabilities") or []
    if not isinstance(caps, list):
        fail("capabilities must be a list")
    unknown = [item for item in caps if item not in CAPABILITIES]
    if unknown:
        fail(f"unknown capabilities: {unknown} (choose from {list(CAPABILITIES)})")
    missing = [item for item in caps if item in UNIMPLEMENTED_CAPABILITIES]
    if missing:
        fail(f"no canonical implementation for: {missing}")
    if "worker" in caps and "redis" not in caps:
        fail("worker requires redis")


def apply_markers(text: str, disabled: set[str]) -> str:
    """Drop regions whose name is disabled. Marker lines themselves are removed."""
    out: list[str] = []
    stack: list[tuple[str, bool]] = []
    for line in text.splitlines(keepends=True):
        raw = line.rstrip("\r\n")
        begin = _BEGIN.match(raw)
        if begin:
            name = begin.group(2)
            parent_on = all(enabled for _, enabled in stack)
            stack.append((name, parent_on and name not in disabled))
            continue
        end = _END.match(raw)
        if end:
            if not stack or stack[-1][0] != end.group(2):
                fail(f"capability marker mismatch at {raw.strip()}")
            stack.pop()
            continue
        if stack and not stack[-1][1]:
            continue
        out.append(line)
    if stack:
        fail(f"unclosed marker {stack[-1][0]}")
    return "".join(out)


def apply_selection(target: Path, answers: dict) -> None:
    identity = answers["identity"]
    caps = list(answers.get("capabilities") or [])
    pkg = answers["python_package"]
    disabled = _disabled(identity, caps, list(answers["clients"]))
    _rewrite_verifier(target, identity, pkg)
    _rewrite_settings(target, identity, pkg)
    if identity == "wechat":
        _splice_wechat_openapi(target)
    _apply_marker_files(target, pkg, disabled, identity)
    if "redis" not in caps:
        _without_redis(target)
    if "worker" not in caps:
        worker = target / "apps" / "backend" / "src" / pkg / "entrypoints" / "worker.py"
        if worker.exists():
            worker.unlink()
    if _prune_dependencies(target, caps):
        print("[create-project] pyproject dependencies match selected capabilities")
    lock = target / "uv.lock"
    pyproject = target / "apps" / "backend" / "pyproject.toml"
    if lock.is_file() and pyproject.is_file():
        _uv_lock(target)
    for name in ("check_generator.py", "check_wechat_contract.py"):
        script = target / "scripts" / "quality" / name
        if script.is_file():
            script.unlink()
    print(f"[create-project] identity={identity} capabilities={caps or 'none'}")


_DEP_LINE = re.compile(r'^\s*"([A-Za-z0-9_.-]+)(?:\[[^\]]*\])?(?:[<>=!~].*)?",\s*$')


def prune_dependency_text(text: str, caps: list[str]) -> str:
    """Drop redis/arq dependency lines that the selected capabilities do not use."""
    drop: set[str] = set()
    if "redis" not in caps:
        drop.add("redis")
    if "worker" not in caps:
        drop.add("arq")
    if not drop:
        return text
    kept: list[str] = []
    for line in text.splitlines(keepends=True):
        match = _DEP_LINE.match(line.rstrip("\r\n"))
        if match and match.group(1) in drop:
            continue
        kept.append(line)
    return "".join(kept)


def _prune_dependencies(target: Path, caps: list[str]) -> bool:
    path = target / "apps" / "backend" / "pyproject.toml"
    if not path.exists():
        return False
    original = path.read_text(encoding="utf-8")
    updated = prune_dependency_text(original, caps)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def _uv_lock(target: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        fail("uv is required to relock the generated project")
    print("[create-project] uv lock")
    result = subprocess.run(
        [uv, "lock"],
        cwd=target,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if result.returncode != 0:
        print(result.stdout[-2000:], file=sys.stderr)
        print(result.stderr[-2000:], file=sys.stderr)
        fail("uv lock failed in the generated project")


def _disabled(identity: str, caps: list[str], clients: list[str] | None = None) -> set[str]:
    disabled: set[str] = {"template-only"}
    if "redis" not in caps:
        disabled.add("capability:redis")
    if "worker" not in caps:
        disabled.add("capability:worker")
    if identity == "keycloak":
        disabled.add("identity:hs256")
    if clients is not None:
        for client in ("web-vite", "web-next", "wechat-native", "mobile-flutter"):
            if client not in clients:
                disabled.add(f"client:{client}")
    return disabled


def _rewrite_verifier(target: Path, identity: str, pkg: str) -> None:
    root = target / "apps" / "backend" / "src" / pkg / "platform" / "authn"
    active = root / "active.py"
    text = active.read_text(encoding="utf-8")
    if "verifiers.local" not in text:
        fail("active.py is missing the verifiers.local import")
    active.write_text(
        text.replace("verifiers.local", f"verifiers.{identity}"),
        encoding="utf-8",
        newline="\n",
    )
    ver_dir = root / "verifiers"
    for name in IDENTITIES:
        if name == identity:
            continue
        path = ver_dir / f"{name}.py"
        if path.exists():
            path.unlink()
    security = target / "apps" / "backend" / "tests" / "security"
    for name, fname in _TEST_FILES.items():
        if name != identity:
            path = security / fname
            if path.exists():
                path.unlink()
    exports = security / "test_verifier_exports.py"
    if exports.exists():
        exports.unlink()
    if identity == "keycloak":
        secrets = security / "test_settings_secrets.py"
        if secrets.exists():
            secrets.unlink()
    counter = target / "scripts" / "quality" / "check_counterexamples.py"
    mutated = counter.read_text(encoding="utf-8")
    mutated = mutated.replace(
        "platform/authn/verifiers/local.py",
        f"platform/authn/verifiers/{identity}.py",
    )
    mutated = mutated.replace(
        "tests/security/test_authn_verifier.py::test_forged_token_rejected",
        f"tests/security/{_TEST_FILES[identity]}::test_forged_token_rejected",
    )
    counter.write_text(mutated, encoding="utf-8", newline="\n")


def _rewrite_settings(target: Path, identity: str, pkg: str) -> None:
    if identity == "local":
        return
    path = target / "apps" / "backend" / "src" / pkg / "platform" / "config" / "settings.py"
    text = path.read_text(encoding="utf-8")
    block = _WECHAT_BLOCK if identity == "wechat" else _KEYCLOAK_BLOCK
    replaced, count = _IDENTITY_REGION.subn(
        lambda m: m.group(1) + block + m.group(3), text, count=1
    )
    if count != 1:
        fail("settings.py is missing the identity region")
    import_line = (_WECHAT_IMPORT if identity == "wechat" else _KEYCLOAK_IMPORT).format(pkg=pkg)
    needle = "from pydantic import SecretStr, model_validator\n"
    if needle not in replaced:
        fail("settings.py is missing the pydantic import")
    path.write_text(
        replaced.replace(needle, needle + import_line, 1),
        encoding="utf-8",
        newline="\n",
    )


def _splice_wechat_openapi(target: Path) -> None:
    path = target / "contracts" / "http" / "openapi.yaml"
    text = path.read_text(encoding="utf-8")
    if "/api/v1/session/wechat:" in text:
        return
    if "\npaths:\n" not in text or "\ncomponents:\n" not in text:
        fail("openapi.yaml has no paths/components markers for the wechat session splice")
    text = text.replace("\npaths:\n", "\n" + _WECHAT_TAG + "paths:\n", 1)
    text = text.replace("\ncomponents:\n", "\n" + _WECHAT_PATH + "components:\n", 1)
    path.write_text(text, encoding="utf-8", newline="\n")


def _marker_files(pkg: str) -> list[str]:
    src = f"apps/backend/src/{pkg}"
    return [
        "infra/compose/compose.yaml",
        "infra/compose/compose.dev.yaml",
        "infra/compose/compose.test.yaml",
        ".github/workflows/ci.yaml",
        ".env.example",
        "apps/backend/.env.example",
        "infra/config/staging.env.example",
        "scripts/dev/doctor.py",
        f"{src}/platform/config/settings.py",
        f"{src}/platform/capabilities.py",
        "apps/backend/tests/contract/test_observability.py",
        "Makefile",
    ]


def _apply_marker_files(target: Path, pkg: str, disabled: set[str], identity: str) -> None:
    for rel in _marker_files(pkg):
        path = target / rel
        if not path.exists():
            continue
        text = apply_markers(path.read_text(encoding="utf-8"), disabled)
        text = _fill_env(text, identity)
        path.write_text(text, encoding="utf-8", newline="\n")


def _fill_env(text: str, identity: str) -> str:
    out: list[str] = []
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped not in ("# identity:env-compose", "# identity:env-file"):
            out.append(line)
            continue
        indent = line[: len(line) - len(line.lstrip(" "))]
        items = _COMPOSE_ENV if stripped.endswith("compose") else _FILE_ENV
        for item in items.get(identity, ()):
            newline = "\n" if line.endswith("\n") else ""
            out.append(f"{indent}{item}{newline}")
    return "".join(out)


def _without_redis(target: Path) -> None:
    run = target / "tests" / "e2e" / "run.sh"
    if run.exists():
        text = run.read_text(encoding="utf-8")
        text = text.replace("postgres + redis", "postgres").replace("postgres redis", "postgres")
        run.write_text(text, encoding="utf-8", newline="\n")
    spec = target / "contracts" / "http" / "openapi.yaml"
    if spec.exists():
        text = spec.read_text(encoding="utf-8")
        text = text.replace(
            "Returns 200 when DB and Redis answer",
            "Returns 200 when the database answers",
        )
        spec.write_text(text, encoding="utf-8", newline="\n")
