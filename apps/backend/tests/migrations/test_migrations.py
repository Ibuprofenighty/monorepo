"""Migration tests: empty DB → head, constraints enforced (blueprint 04 §6).

Requires TEST_DATABASE_URL=postgresql+asyncpg://... Skipped otherwise.
The single controlled executor path is exercised: alembic upgrade head.
"""

import os
import subprocess
from pathlib import Path

import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="needs TEST_DATABASE_URL (real PostgreSQL)")

BACKEND = Path(__file__).resolve().parents[2]


def _alembic(*args: str) -> None:
    env = dict(os.environ, DATABASE_URL=TEST_DB)
    subprocess.run(
        ["alembic", "-c", str(BACKEND / "alembic.ini"), *args],
        cwd=BACKEND,
        env=env,
        check=True,
        capture_output=True,
    )


async def test_upgrade_head_applies_cleanly():
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    # idempotent re-run must not fail
    _alembic("upgrade", "head")


async def test_unique_constraint_enforced_after_migration():
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.ext.asyncio import create_async_engine

    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    engine = create_async_engine(TEST_DB)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO catalog_resources (id, name, locked) VALUES ('a','n',false)")
            )
            with pytest.raises(IntegrityError):
                await conn.execute(
                    text("INSERT INTO catalog_resources (id, name, locked) VALUES ('b','n',false)")
                )
    finally:
        await engine.dispose()
    _alembic("downgrade", "base")


async def test_idempotency_primary_key_is_subject_and_key():
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.ext.asyncio import create_async_engine

    insert = text(
        "INSERT INTO catalog_idempotency_keys (subject, key, body_hash, status_code, response_body)"
        " VALUES (:subject, 'k', 'h', 201, '{}')"
    )
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    engine = create_async_engine(TEST_DB)
    try:
        async with engine.begin() as conn:
            await conn.execute(insert, {"subject": "alice"})
            await conn.execute(insert, {"subject": "bob"})
            with pytest.raises(IntegrityError):
                await conn.execute(insert, {"subject": "alice"})
    finally:
        await engine.dispose()
    _alembic("downgrade", "base")
