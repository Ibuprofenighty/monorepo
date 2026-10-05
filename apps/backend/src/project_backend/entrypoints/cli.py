"""CLI entrypoint.

    python -m project_backend.entrypoints.cli seed
    python -m project_backend.entrypoints.cli mint-token --subject alice --role editor

`mint-token` issues a token signed with the configured verifier and is refused
when APP_ENV is staging/production (dev/test tooling only, e.g. tests/e2e).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from project_backend.bootstrap.container import build_container
from project_backend.kernel.identity import Principal
from project_backend.modules.catalog.infrastructure.persistence.models import ResourceORM
from project_backend.platform.authn.active import build_verifier, mint_token
from project_backend.platform.authn.protocol import UnsupportedMint
from project_backend.platform.config.settings import Settings

SYSTEM = Principal(subject="system:cli", roles=frozenset({"editor"}))
SEED_NAME = "Demo resource (seed)"


async def seed() -> None:
    """Seed demo data through the ORM directly (documented exception: seed data,
    not business logic — never copy use-case rules here). Idempotent."""
    container = build_container(Settings())
    async with container.session_factory() as session:
        async with session.begin():
            existing = await session.scalar(
                select(ResourceORM.id).where(ResourceORM.name == SEED_NAME)
            )
            if existing is not None:
                print(f"seed: {SEED_NAME!r} already present, skipping")
                return
            session.add(
                ResourceORM(
                    id=f"res_{uuid4().hex[:12]}",
                    name=SEED_NAME,
                    locked=False,
                    created_at=datetime.now(UTC),
                )
            )
    await container.engine.dispose()
    print("seeded 1 demo resource")


def mint(subject: str, roles: list[str], expires_minutes: int) -> int:
    settings = Settings()
    if settings.is_deployed:
        print(f"refusing: mint-token is not available when APP_ENV={settings.app_env}")
        return 1
    try:
        token = mint_token(build_verifier(settings), subject, frozenset(roles), expires_minutes)
    except UnsupportedMint as exc:
        print(f"refusing: {exc}")
        return 1
    print(token)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", help="seed demo data")
    mt = sub.add_parser("mint-token", help="issue a dev/test bearer token")
    mt.add_argument("--subject", required=True)
    mt.add_argument("--role", action="append", default=[], dest="roles")
    mt.add_argument("--expires-minutes", type=int, default=30)
    args = ap.parse_args()
    if args.command == "seed":
        asyncio.run(seed())
        return 0
    return mint(args.subject, args.roles, args.expires_minutes)


if __name__ == "__main__":
    sys.exit(main())
