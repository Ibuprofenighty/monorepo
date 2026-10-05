"""Port implementations. Translate DB errors to domain errors here —
never parse unstable DB messages for public codes (blueprint 03 §6)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from project_backend.modules.catalog.application.ports.repository import (
    IdempotencyKeyInUse,
    IdempotencyRecord,
    IdempotencyStore,
    ResourceRepository,
)
from project_backend.modules.catalog.domain.errors import DuplicateResource
from project_backend.modules.catalog.domain.resource import Resource
from project_backend.modules.catalog.infrastructure.persistence.models import (
    IdempotencyKeyORM,
    ResourceORM,
)


def _to_domain(o: ResourceORM) -> Resource:
    return Resource(id=o.id, name=o.name, locked=o.locked, created_at=o.created_at)


class SqlAlchemyResourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, resource_id: str) -> Resource | None:
        o = await self._s.get(ResourceORM, resource_id)
        return _to_domain(o) if o else None

    async def list(self, page: int, page_size: int) -> tuple[list[Resource], int]:
        total = (await self._s.execute(select(func.count()).select_from(ResourceORM))).scalar_one()
        rows = (
            await self._s.execute(
                select(ResourceORM)
                .order_by(ResourceORM.created_at.desc(), ResourceORM.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars()
        return [_to_domain(o) for o in rows], total

    async def add(self, resource: Resource) -> None:
        self._s.add(
            ResourceORM(
                id=resource.id,
                name=resource.name,
                locked=resource.locked,
                created_at=resource.created_at,
            )
        )
        try:
            await self._s.flush()
        except IntegrityError as e:
            raise DuplicateResource(resource.name) from e

    async def remove(self, resource: Resource) -> None:
        o = await self._s.get(ResourceORM, resource.id)
        if o is not None:
            await self._s.delete(o)


class SqlAlchemyIdempotencyStore:
    """Rows are keyed by (subject, key); the primary key serializes concurrent writers."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, subject: str, key: str) -> IdempotencyRecord | None:
        o = await self._s.get(IdempotencyKeyORM, (subject, key))
        if o is None:
            return None
        return IdempotencyRecord(
            subject=o.subject,
            key=o.key,
            body_hash=o.body_hash,
            status_code=o.status_code,
            response_body=o.response_body,
            created_at=o.created_at,
        )

    async def add(self, record: IdempotencyRecord) -> None:
        self._s.add(
            IdempotencyKeyORM(
                subject=record.subject,
                key=record.key,
                body_hash=record.body_hash,
                status_code=record.status_code,
                response_body=record.response_body,
                created_at=record.created_at,
            )
        )
        try:
            await self._s.flush()
        except IntegrityError as e:
            raise IdempotencyKeyInUse(record.key) from e

    async def remove(self, subject: str, key: str) -> None:
        await self._s.execute(
            delete(IdempotencyKeyORM)
            .where(IdempotencyKeyORM.subject == subject, IdempotencyKeyORM.key == key)
            .execution_options(synchronize_session="fetch")
        )

    async def purge_created_before(self, cutoff: datetime) -> int:
        removed = await self._s.execute(
            delete(IdempotencyKeyORM)
            .where(IdempotencyKeyORM.created_at < cutoff)
            .returning(IdempotencyKeyORM.key)
            .execution_options(synchronize_session=False)
        )
        return len(removed.all())


class SqlAlchemyUnitOfWork:
    """Implements the UnitOfWork port. Owns commit/rollback — repositories don't."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session
        self.resources: ResourceRepository = SqlAlchemyResourceRepository(session)
        self.idempotency: IdempotencyStore = SqlAlchemyIdempotencyStore(session)

    async def commit(self) -> None:
        await self._s.commit()

    async def rollback(self) -> None:
        await self._s.rollback()

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        return self

    async def __aexit__(self, *exc: object) -> None:
        if exc[0] is not None:
            await self._s.rollback()
        # commit is explicit in use cases; never auto-commit here.
