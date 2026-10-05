"""Ports (interfaces) owned by the application layer (blueprint 04 §2).

Infrastructure implements these. Application never imports SQLAlchemy/Redis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from project_backend.modules.catalog.domain.resource import Resource


class ResourceRepository(Protocol):
    async def get(self, resource_id: str) -> Resource | None: ...
    async def list(self, page: int, page_size: int) -> tuple[list[Resource], int]: ...
    async def add(self, resource: Resource) -> None:
        """Stage and flush. Raises DuplicateResource when the name is taken."""
        ...

    async def remove(self, resource: Resource) -> None: ...


@dataclass(frozen=True)
class IdempotencyRecord:
    """Stored outcome of one successful idempotent request, scoped to (subject, key)."""

    subject: str
    key: str
    body_hash: str
    status_code: int
    response_body: dict
    created_at: datetime


class IdempotencyKeyInUse(Exception):
    """Another transaction already holds (subject, key). Raised by IdempotencyStore.add."""


class IdempotencyStore(Protocol):
    """Participates in the UnitOfWork transaction; never commits on its own."""

    async def get(self, subject: str, key: str) -> IdempotencyRecord | None: ...
    async def add(self, record: IdempotencyRecord) -> None:
        """Stage and flush. Raises IdempotencyKeyInUse when (subject, key) exists."""
        ...

    async def remove(self, subject: str, key: str) -> None: ...
    async def purge_created_before(self, cutoff: datetime) -> int: ...


class UnitOfWork(Protocol):
    """Transaction boundary. Repositories and stores never commit (blueprint 04 §5)."""

    resources: ResourceRepository
    idempotency: IdempotencyStore

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def __aenter__(self) -> UnitOfWork: ...
    async def __aexit__(self, *exc: object) -> None: ...
