"""Worker entrypoint. Reuses the SAME use cases as HTTP (blueprint 04 §9).

Run:  python -m project_backend.entrypoints.worker
(No JWT/session secrets are copied into job messages.)
"""

from __future__ import annotations

from arq import cron, run_worker
from arq.connections import RedisSettings
from arq.typing import WorkerSettingsBase

from project_backend.bootstrap.container import Container, build_container
from project_backend.modules.catalog import public
from project_backend.modules.catalog.wiring import get_uow
from project_backend.platform.config.settings import Settings


async def catalog_maintenance(ctx: dict) -> str:
    """Hourly: purge idempotency records past their TTL."""
    container: Container = ctx["container"]
    async with container.session_factory() as session:
        removed = await public.purge_expired_idempotency(get_uow(session))
    return f"catalog maintenance ok, purged_idempotency={removed}"


class WorkerSettings(WorkerSettingsBase):
    functions = [catalog_maintenance]
    cron_jobs = [cron(catalog_maintenance, minute=0, unique=True)]
    redis_settings = RedisSettings.from_dsn(Settings().redis_url)

    @staticmethod
    async def on_startup(ctx: dict) -> None:
        ctx["container"] = build_container(Settings())


def main() -> None:
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()
