#!/usr/bin/env python3
"""Doc checks (blueprint 09 §7): links resolve, required entries exist.

- Every relative .md link in docs/ and README.md must resolve to a file.
- Fragment links (#...) must match a heading in the target file.
- docs/blueprint/ must contain the full canonical set (00-12 + SOURCES + VALIDATION).
- No absolute local paths (e.g. /home/..., C:\\Users\\...) leaked into docs.

Exit 1 on any violation. Usage: python scripts/quality/check_docs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(#[^)\s]*)?\)")
ABS_PATH_RE = re.compile(r"(?:/(?:home|Users|tmp)/|\b[A-Za-z]:[\\/](?:Users|home)[\\/])[\w.-]+")
SKIP_DIRS = {"node_modules", ".dart_tool", "build", "dist", ".next"}

REQUIRED_BLUEPRINT = [f"{i:02d}-" for i in range(13)] + ["SOURCES.md", "VALIDATION.md"]


def _headings(path: Path) -> set[str]:
    heads = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"#{1,6}\s+(.*)", line)
        if m:
            slug = re.sub(r"[^\w\s-]", "", m.group(1).lower()).strip().replace(" ", "-")
            heads.add(slug)
    return heads


def _check_changelog(errors: list[str]) -> None:
    directory = ROOT / "docs" / "changelog"
    if not directory.is_dir():
        errors.append("docs/changelog missing")
        return
    entries = sorted(p for p in directory.glob("*.md") if p.name != "README.md")
    if not entries:
        errors.append("docs/changelog: at least one entry is required")
    for entry in entries:
        text = entry.read_text(encoding="utf-8")
        rel = entry.relative_to(ROOT)
        if "## 变更" not in text:
            errors.append(f"{rel}: missing heading ## 变更")
        if "## 已生成项目同步" not in text:
            errors.append(f"{rel}: missing heading ## 已生成项目同步")


def main() -> int:
    errors: list[str] = []
    md_files = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "apps").rglob("*.md")),
        *sorted((ROOT / "packages").rglob("*.md")),
    ]
    md_files = [
        f for f in md_files if f.exists() and not SKIP_DIRS.intersection(f.relative_to(ROOT).parts)
    ]

    for md in md_files:
        text = md.read_text(encoding="utf-8")
        for m in ABS_PATH_RE.finditer(text):
            # allow the templates' own examples only if clearly marked; flag all for review
            errors.append(f"{md.relative_to(ROOT)}: absolute local path {m.group(0)!r}")
        for lm in LINK_RE.finditer(text):
            target, frag = lm.group(1), lm.group(2)
            is_external = target.startswith(("http://", "https://", "mailto:", "#"))
            if is_external or not target.endswith(".md"):
                continue
            resolved = (md.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"{md.relative_to(ROOT)}: link escapes repo: {target}")
                continue
            if not resolved.exists():
                errors.append(f"{md.relative_to(ROOT)}: broken link → {target}")
            elif frag:
                # docs/blueprint/ is the verbatim canonical import; its SOURCES
                # shorthand anchors (#s36) are the blueprint author's own
                # convention — don't rewrite canonical docs to satisfy the linter.
                rel_parts = md.relative_to(ROOT).parts
                if rel_parts[0] == "docs" and rel_parts[1] == "blueprint":
                    continue
                slug = frag[1:].lower()
                if slug not in _headings(resolved):
                    errors.append(f"{md.relative_to(ROOT)}: broken fragment {frag} in {target}")

    bp = ROOT / "docs" / "blueprint"
    if bp.exists():
        names = [f.name for f in bp.glob("*.md")]
        for req in REQUIRED_BLUEPRINT:
            if not any(n.startswith(req) if req.endswith("-") else n == req for n in names):
                errors.append(f"docs/blueprint: missing required {req}")
    # generated projects don't carry docs/blueprint/ — the requirement only
    # applies to the mother template.

    _check_changelog(errors)

    if errors:
        print("DOC CHECK FAILURES:")
        for e in errors:
            print(" ", e)
        return 1
    print(f"check-docs: ok ({len(md_files)} files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
