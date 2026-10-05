# Backend — headless Python API (blueprint 04)

Module layout per domain (`src/project_backend/modules/<name>/`):

```text
domain/            # pure business state + invariants. No HTTP, no DB, no config.
application/       # use cases: commands/queries, ports/, access.py. Owns transactions.
infrastructure/    # implements ports: SQLAlchemy models, repositories, integrations.
presentation/      # protocol adapters: FastAPI router, mapping, error_mapping.
public.py          # THE stable cross-module API. Other modules import only this.
wiring.py          # factories + error mapping for bootstrap.
```

Dependency direction (checked by `make check-architecture`):

```text
presentation → application → domain
infrastructure → application.ports + domain
platform → kernel + tech libs
bootstrap → wiring + platform
```

## Commands

```bash
uv sync --all-extras
uv run uvicorn project_backend.entrypoints.http:app --reload   # API
uv run python -m project_backend.entrypoints.worker            # arq worker
uv run python -m project_backend.entrypoints.cli seed          # seed demo data
uv run pytest -q
uv run alembic revision --autogenerate -m "..." && uv run alembic upgrade head
```

The container image runs the same entrypoint:
`uvicorn project_backend.entrypoints.http:app --host 0.0.0.0 --port 8000`.
Migrations are never run on startup; `scripts/ops/migrate.py` applies them.

## Configuration

`platform/config/settings.py` (pydantic-settings, env vars or `.env`; see `.env.example`):

| Var | Notes |
|---|---|
| `APP_ENV` | `dev` / `test` / `staging` / `production` |
| `DATABASE_URL`, `REDIS_URL` | asyncpg / redis DSNs |
| `JWT_SECRET` | HS256 key. `staging` / `production` refuse to start unless it is injected and ≥ 32 bytes; `dev` / `test` fall back to a built-in dev key |

## Idempotent create (`POST /resources`)

- `Idempotency-Key` (1–64 chars) is scoped to the authenticated subject: two callers
  can reuse the same key independently.
- Same subject + key + body within 24 h → the stored `201` response is replayed;
  same key with a different body → `422` (`VALIDATION.FAILED`).
- Authorization runs before replay, so a revoked caller never sees a stored result.
- The idempotency record and the resource commit in one transaction; failures store
  nothing. Concurrent requests with one key create exactly one resource
  (primary key `(subject, key)`).
- The worker's hourly `catalog_maintenance` cron purges expired records.

The served OpenAPI is the hand-written `contracts/http/openapi.yaml`
(`bootstrap/app.py` overrides `app.openapi()`); routes MUST stay conformant —
`tests/contract/` proves it on every run.
