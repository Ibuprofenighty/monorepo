"""Use-case level idempotency paths that HTTP tests cannot stage deterministically."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from project_backend.modules.catalog.application.commands.create_resource import (
    IDEMPOTENCY_TTL,
    CreateResourceCommand,
    create_resource,
    purge_expired_idempotency,
    request_body_hash,
)
from project_backend.modules.catalog.application.ports.repository import (
    IdempotencyKeyInUse,
    IdempotencyRecord,
)

from tests.conftest import EDITOR, AllowAll, FakeIdempotency, FakeRepo, FakeUoW


class RacingIdempotency(FakeIdempotency):
    """Another transaction commits the same (subject, key) between our lookup and insert.

    The winner lives outside this transaction's snapshot, so our rollback cannot undo it.
    """

    def __init__(self, winner: IdempotencyRecord) -> None:
        super().__init__()
        self._winner = winner
        self._winner_committed = False

    def _is_winner(self, subject: str, key: str) -> bool:
        return self._winner_committed and (subject, key) == (self._winner.subject, self._winner.key)

    async def get(self, subject: str, key: str) -> IdempotencyRecord | None:
        if self._is_winner(subject, key):
            return self._winner
        self._winner_committed = True
        return await super().get(subject, key)

    async def add(self, record: IdempotencyRecord) -> None:
        if self._is_winner(record.subject, record.key):
            raise IdempotencyKeyInUse(record.key)
        await super().add(record)


def _record(key: str, name: str, created_at: datetime) -> IdempotencyRecord:
    return IdempotencyRecord(
        subject=EDITOR.subject,
        key=key,
        body_hash=request_body_hash(name),
        status_code=201,
        response_body={
            "id": "res_winner",
            "name": name,
            "locked": False,
            "created_at": created_at.isoformat(),
        },
        created_at=created_at,
    )


# spec: CATALOG.CREATE.IDEMPOTENCY_CONCURRENT
async def test_concurrent_same_key_loser_replays_winner():
    repo = FakeRepo()
    winner = _record("race", "raced", datetime.now(UTC))
    idem = RacingIdempotency(winner)
    uow = FakeUoW(repo, idem)

    result = await create_resource(
        CreateResourceCommand(name="raced", principal=EDITOR, idempotency_key="race"),
        uow,
        AllowAll(),
    )

    assert result.id == "res_winner"
    assert repo._store == {}  # the loser wrote nothing of its own
    assert uow.commits == 0


async def test_purge_removes_only_expired_records():
    now = datetime.now(UTC)
    idem = FakeIdempotency()
    expired_at = now - IDEMPOTENCY_TTL - timedelta(seconds=1)
    idem._store[(EDITOR.subject, "old")] = _record("old", "a", expired_at)
    idem._store[(EDITOR.subject, "new")] = _record("new", "b", now)
    uow = FakeUoW(FakeRepo(), idem)

    removed = await purge_expired_idempotency(uow, now=now)

    assert removed == 1
    assert list(idem._store) == [(EDITOR.subject, "new")]
    assert uow.commits == 1
