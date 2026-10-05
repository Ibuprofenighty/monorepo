"""Readiness dependencies. Marked blocks are removed when a capability is not selected."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from project_backend.platform.config.settings import Settings


async def dependency_checks(settings: Settings, engine: AsyncEngine) -> dict[str, str]:
    checks: dict[str, str] = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:  # noqa: BLE001 — readiness reports, never raises
        checks["database"] = f"error: {type(e).__name__}"

    # begin capability:redis
    import redis.asyncio

    try:
        client = redis.asyncio.from_url(settings.redis_url, socket_timeout=2)
        await client.ping()
        await client.aclose()
        checks["redis"] = "ok"
    except Exception as e:  # noqa: BLE001 — readiness reports, never raises
        checks["redis"] = f"error: {type(e).__name__}"
    # end capability:redis
    return checks
