#!/usr/bin/env python3
"""Directed counterexample harness (blueprint 10 §5-§6).

For each key rule, plants a controlled fault (mutation) into the source,
runs the designated test, and expects it to FAIL. A mutation the tests do
NOT catch is the real finding — it means the rule is unguarded.

- Files are always restored (try/finally), even on harness errors.
- Uses sqlite URL so no external DB is needed; the container is built but
  sessions are overridden by test fixtures.
- Exit 0: every mutation was caught. Exit 1: a mutation slipped through
  (or the harness itself broke).

Usage: python scripts/quality/check_counterexamples.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "apps" / "backend"
SRC = BACKEND / "src" / "project_backend"


def _resolve_pytest() -> list[str]:
    """pytest runner: $PYTEST_BIN > uv run > sys.executable -m pytest."""
    override = os.environ.get("PYTEST_BIN")
    if override:
        return override.split()
    if shutil.which("uv"):
        return ["uv", "run", "--project", str(BACKEND), "--frozen", "--extra", "dev", "pytest"]
    return [sys.executable, "-m", "pytest"]


PYTEST = _resolve_pytest() + ["-q", "-p", "no:cacheprovider"]


@dataclass(frozen=True)
class Mutation:
    name: str
    file: Path  # relative to SRC
    old: str  # exact text to replace
    new: str  # mutated text
    test_node: str  # pytest node id expected to FAIL under mutation
    why: str


MUTATIONS: list[Mutation] = [
    Mutation(
        name="remove-locked-invariant",
        file=Path("modules/catalog/domain/resource.py"),
        old="""    def ensure_deletable(self) -> None:
        \"\"\"INVARIANT CATALOG.DELETE.LOCKED_NO_EFFECT: locked resources cannot be deleted.\"\"\"
        if self.locked:
            raise ResourceLocked(self.id)""",
        new="""    def ensure_deletable(self) -> None:
        \"\"\"INVARIANT CATALOG.DELETE.LOCKED_NO_EFFECT: locked resources cannot be deleted.\"\"\"
        if False:  # MUTATION planted by check_counterexamples.py
            raise ResourceLocked(self.id)""",
        test_node="tests/modules/catalog/unit/test_domain.py::test_locked_resource_is_not_deletable",
        why="locked resources must be undeletable (catalog invariant)",
    ),
    Mutation(
        name="verifier-accepts-everything",
        file=Path("platform/authn/verifiers/local.py"),
        old="""def verify_bearer_token(verifier: Verifier, token: str | None) -> Principal:
    if not token:
        raise MappedError(ErrorCode.AUTHN_REQUIRED)""",
        new="""def verify_bearer_token(verifier: Verifier, token: str | None) -> Principal:
    return Principal(subject="mutant", roles=frozenset({"editor"}))  # MUTATION
    if not token:
        raise MappedError(ErrorCode.AUTHN_REQUIRED)""",
        test_node="tests/security/test_authn_verifier.py::test_forged_token_rejected",
        why="forged/invalid tokens must be rejected (authn)",
    ),
    Mutation(
        name="write-before-authorize",
        file=Path("modules/catalog/application/commands/create_resource.py"),
        old="""    # Authorize against a not-yet-persisted candidate (kind-level policy).
    candidate = Resource(id="", name=cmd.name, locked=False, created_at=datetime.now(UTC))
    ensure_can(authorizer, cmd.principal, "resource.create", candidate)
""",
        new="""    # MUTATION planted by check_counterexamples.py: authorize after the write
""",
        test_node="tests/security/test_authz_deny.py::test_deny_before_write_ordering",
        why="deny must happen before any write attempt (no side effects on deny)",
    ),
    Mutation(
        name="write-before-authorize-part2",
        file=Path("modules/catalog/application/commands/create_resource.py"),
        old="""        await uow.resources.add(resource)
        await uow.commit()""",
        new="""        await uow.resources.add(resource)
        candidate = Resource(id="", name=cmd.name, locked=False, created_at=datetime.now(UTC))
        ensure_can(authorizer, cmd.principal, "resource.create", candidate)  # MUTATION: too late
        await uow.commit()""",
        test_node="tests/security/test_authz_deny.py::test_deny_before_write_ordering",
        why="deny must happen before any write attempt (no side effects on deny)",
    ),
    Mutation(
        name="drop-idempotency-subject-scope",
        file=Path("modules/catalog/application/commands/create_resource.py"),
        old="""    subject = cmd.principal.subject
""",
        new="""    subject = "global"  # MUTATION planted by check_counterexamples.py
""",
        test_node=(
            "tests/modules/catalog/api/test_http.py::test_idempotency_key_scoped_per_subject"
        ),
        why="idempotency keys are scoped per principal subject",
    ),
]


def _run_pytest(node: str) -> int:
    env = {
        **os.environ,
        "DATABASE_URL": "sqlite+aiosqlite://",
        "PYTHONPATH": str(BACKEND / "src"),
    }
    r = subprocess.run(
        [*PYTEST, node],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return r.returncode


def _sanity_test_passes(node: str) -> bool:
    """The designated test must pass WITHOUT the mutation first."""
    return _run_pytest(node) == 0


def main() -> int:
    # write-before-authorize is a two-part mutation on the same file; apply
    # both parts together as one logical case.
    grouped: dict[str, list[Mutation]] = {}
    for m in MUTATIONS:
        key = m.name.rsplit("-part2", 1)[0] if m.name.endswith("-part2") else m.name
        grouped.setdefault(key, []).append(m)

    failures = 0
    originals: dict[Path, bytes] = {}
    for name, parts in grouped.items():
        why = parts[0].why
        node = parts[0].test_node
        target = SRC / parts[0].file
        original_bytes = target.read_bytes()
        originals[target] = original_bytes
        original = original_bytes.decode("utf-8")
        missing = [p for p in parts if p.old not in original]
        if missing:
            print(f"[counterexample] {name}: HARNESS-ERROR — anchor drifted in {parts[0].file}")
            failures += 1
            continue
        try:
            if not _sanity_test_passes(node):
                print(f"[counterexample] {name}: HARNESS-ERROR — {node} fails without mutation")
                failures += 1
                continue
            mutated = original
            for p in parts:
                mutated = mutated.replace(p.old, p.new, 1)
            target.write_bytes(mutated.encode("utf-8"))
            code = _run_pytest(node)
            if code != 0:
                print(f"[counterexample] {name}: CAUGHT — {why}")
            else:
                print(f"[counterexample] {name}: MISSED — {node} did not catch it ({why})")
                failures += 1
        finally:
            target.write_bytes(original_bytes)

    # verify byte-exact restoration
    for path, content in originals.items():
        if path.read_bytes() != content:
            print(f"[counterexample] RESTORE-FAILED: {path.relative_to(SRC)}")
            failures += 1

    if failures:
        print(f"[counterexample] {failures} problem(s) — see above")
        return 1
    print("[counterexample] all mutations caught, sources restored")
    return 0


if __name__ == "__main__":
    sys.exit(main())
