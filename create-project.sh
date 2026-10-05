#!/usr/bin/env bash
# New-project generator entry. See scripts/scaffold/README.md.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# Runs in the locked backend environment (pyyaml) via uv; same as on Windows:
#   uv run --project apps/backend --frozen --extra dev python scripts/scaffold/create_project.py ...
exec uv run --project "$ROOT/apps/backend" --frozen --extra dev python "$ROOT/scripts/scaffold/create_project.py" "$@"
