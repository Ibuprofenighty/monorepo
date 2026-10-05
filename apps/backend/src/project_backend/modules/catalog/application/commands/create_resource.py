"""Create resource — protected write use case.

Order (blueprint 04 §4): principal → authorize → validate → write → commit.

Idempotency-Key semantics (blueprint 04 §5, contract parameter IdempotencyKey):
- Scope: (principal subject, key) on POST /api/v1/resources. Keys of different
  subjects never collide; authorization runs before any lookup.
- Fingerprint: SHA-256 of the canonical JSON request body.
- Stored result: only a successful 201 is stored, in the same transaction as the
  resource; failed requests leave no record and may be retried with the key.
- Replay: same scope + same fingerprint → the stored 201 body; different
  fingerprint → IdempotencyConflict.
- Concurrency: the (subject, key) primary key admits exactly one writer; the
  loser rolls back and replays the winner's committed result.
- Expiry: records older than IDEMPOTENCY_TTL are not replayed; they are replaced
  on next use and purged by purge_expired_idempotency.
- Crash recovery: record and resource commit atomically, so a crash leaves
  neither and the client retry executes once.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from project_backend.kernel.authorization import Authorizer
from project_backend.kernel.identity import Principal
from project_backend.modules.catalog.application.access import ensure_can
from project_backend.modules.catalog.application.ports.repository import (
    IdempotencyKeyInUse,
    IdempotencyRecord,
    UnitOfWork,
)
from project_backend.modules.catalog.domain.resource import Resource

IDEMPOTENCY_TTL = timedelta(hours=24)


class IdempotencyConflict(Exception):
    """Same scope and key, different body. Mapped to VALIDATION.FAILED in error_mapping."""

    def __init__(self) -> None:
        super().__init__("Idempotency-Key was already used with a different request body")


@dataclass(frozen=True)
class CreateResourceCommand:
    name: str
    principal: Principal
    idempotency_key: str | None = None


def request_body_hash(name: str) -> str:
    return hashlib.sha256(json.dumps({"name": name}, sort_keys=True).encode()).hexdigest()


def _resource_to_body(r: Resource) -> dict:
    return {"id": r.id, "name": r.name, "locked": r.locked, "created_at": r.created_at.isoformat()}


def _resource_from_body(body: dict) -> Resource:
    return Resource(
        id=body["id"],
        name=body["name"],
        locked=body["locked"],
        created_at=datetime.fromisoformat(body["created_at"]),
    )


async def _replay(uow: UnitOfWork, subject: str, key: str, body_hash: str) -> Resource | None:
    """Stored result for (subject, key), or None when absent or expired (expired is removed)."""
    record = await uow.idempotency.get(subject, key)
    if record is None:
        return None
    if record.created_at <= datetime.now(UTC) - IDEMPOTENCY_TTL:
        await uow.idempotency.remove(subject, key)
        return None
    if record.body_hash != body_hash:
        raise IdempotencyConflict()
    return _resource_from_body(record.response_body)


async def create_resource(
    cmd: CreateResourceCommand,
    uow: UnitOfWork,
    authorizer: Authorizer,
) -> Resource:
    # Authorize against a not-yet-persisted candidate (kind-level policy).
    candidate = Resource(id="", name=cmd.name, locked=False, created_at=datetime.now(UTC))
    ensure_can(authorizer, cmd.principal, "resource.create", candidate)

    subject = cmd.principal.subject
    key = cmd.idempotency_key
    body_hash = request_body_hash(cmd.name)
    async with uow:
        if key is not None:
            replayed = await _replay(uow, subject, key, body_hash)
            if replayed is not None:
                return replayed

        resource = Resource(
            id=f"res_{uuid4().hex[:12]}",
            name=cmd.name,
            locked=False,
            created_at=datetime.now(UTC),
        )
        if key is not None:
            try:
                await uow.idempotency.add(
                    IdempotencyRecord(
                        subject=subject,
                        key=key,
                        body_hash=body_hash,
                        status_code=201,
                        response_body=_resource_to_body(resource),
                        created_at=resource.created_at,
                    )
                )
            except IdempotencyKeyInUse:
                await uow.rollback()
                replayed = await _replay(uow, subject, key, body_hash)
                if replayed is None:
                    raise
                return replayed

        await uow.resources.add(resource)
        await uow.commit()
    return resource


async def purge_expired_idempotency(uow: UnitOfWork, now: datetime | None = None) -> int:
    """Delete idempotency records past IDEMPOTENCY_TTL. Returns the number removed."""
    cutoff = (now or datetime.now(UTC)) - IDEMPOTENCY_TTL
    async with uow:
        removed = await uow.idempotency.purge_created_before(cutoff)
        await uow.commit()
    return removed
