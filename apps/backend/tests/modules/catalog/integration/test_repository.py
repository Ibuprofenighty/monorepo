"""Repository integration tests against REAL PostgreSQL (blueprint 10 §2, §9).

Requires TEST_DATABASE_URL=postgresql+asyncpg://... Skipped otherwise.
SQLite is NOT an acceptable substitute for PG semantics.
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta

import pytest
from project_backend.kernel.identity import Principal
from project_backend.modules.catalog.application.access import LocalAuthorizer
from project_backend.modules.catalog.application.commands.create_resource import (
    CreateResourceCommand,
    create_resource,
    purge_expired_idempotency,
)
from project_backend.modules.catalog.application.ports.repository import (
    IdempotencyKeyInUse,
    IdempotencyRecord,
)
from project_backend.modules.catalog.domain.resource import Resource
from project_backend.modules.catalog.infrastructure.persistence.repository import (
    SqlAlchemyUnitOfWork,
)
from project_backend.platform.db.base import Base
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

TEST_DB = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="needs TEST_DATABASE_URL (real PostgreSQL)")


@pytest.fixture
async def session_factory():
    engine = create_async_engine(TEST_DB, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _res(rid="res_1", name="n", locked=False) -> Resource:
    return Resource(id=rid, name=name, locked=locked, created_at=datetime.now(UTC))


async def test_add_get_roundtrip(session_factory):
    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            await uow.resources.add(_res())
            await uow.commit()
    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            got = await uow.resources.get("res_1")
    assert got is not None and got.name == "n"


async def test_unique_name_violates_constraint(session_factory):
    from project_backend.modules.catalog.domain.errors import DuplicateResource

    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            await uow.resources.add(_res("res_1", name="dup"))
            await uow.commit()
    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            with pytest.raises(DuplicateResource):
                await uow.resources.add(_res("res_2", name="dup"))
            await uow.rollback()
    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            assert await uow.resources.get("res_2") is None


async def test_list_pagination(session_factory):
    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            for i in range(3):
                await uow.resources.add(_res(f"res_{i}", name=f"n{i}"))
            await uow.commit()
    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            items, total = await uow.resources.list(1, 2)
    assert total == 3 and len(items) == 2


def _record(subject: str, key: str, created_at: datetime | None = None) -> IdempotencyRecord:
    return IdempotencyRecord(
        subject=subject,
        key=key,
        body_hash="hash1",
        status_code=201,
        response_body={"id": "res_1"},
        created_at=created_at or datetime.now(UTC),
    )


async def test_idempotency_store_scoped_by_subject(session_factory):
    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            assert await uow.idempotency.get("alice", "k") is None
            await uow.idempotency.add(_record("alice", "k"))
            await uow.idempotency.add(_record("bob", "k"))
            await uow.commit()
    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            got = await uow.idempotency.get("alice", "k")
            assert got is not None and got.response_body == {"id": "res_1"}
            assert await uow.idempotency.get("carol", "k") is None


async def test_idempotency_store_rejects_same_scope(session_factory):
    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            await uow.idempotency.add(_record("alice", "k"))
            await uow.commit()
    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            with pytest.raises(IdempotencyKeyInUse):
                await uow.idempotency.add(_record("alice", "k"))


async def test_idempotency_purge_removes_only_expired(session_factory):
    now = datetime.now(UTC)
    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            await uow.idempotency.add(_record("alice", "old", now - timedelta(days=2)))
            await uow.idempotency.add(_record("alice", "new", now))
            await uow.commit()
    async with session_factory() as s:
        assert await purge_expired_idempotency(SqlAlchemyUnitOfWork(s), now=now) == 1
    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            assert await uow.idempotency.get("alice", "old") is None
            assert await uow.idempotency.get("alice", "new") is not None


# spec: CATALOG.CREATE.IDEMPOTENCY_CONCURRENT
async def test_concurrent_same_key_creates_once(session_factory):
    principal = Principal(subject="alice", roles=frozenset({"editor"}))

    async def attempt() -> str:
        async with session_factory() as s:
            created = await create_resource(
                CreateResourceCommand(name="raced", principal=principal, idempotency_key="race"),
                SqlAlchemyUnitOfWork(s),
                LocalAuthorizer(),
            )
            return created.id

    ids = await asyncio.gather(*(attempt() for _ in range(5)))

    assert len(set(ids)) == 1
    async with session_factory() as s:
        uow = SqlAlchemyUnitOfWork(s)
        async with uow:
            items, total = await uow.resources.list(1, 10)
    assert total == 1 and items[0].id == ids[0]
