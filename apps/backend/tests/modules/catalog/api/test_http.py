"""HTTP layer tests: contract shapes + Problem errors. Persistence is faked;
the boundary under test is router → use case → mapping."""

from datetime import UTC, datetime, timedelta

from project_backend.kernel.identity import Principal
from project_backend.modules.catalog.domain.resource import Resource
from project_backend.platform.http import deps as http_deps

from tests.conftest import EDITOR, VIEWER, DenyWrites, make_client


def _seed(repo, **kw):
    r = Resource(
        id=kw.get("id", "res_1"),
        name=kw.get("name", "seeded"),
        locked=kw.get("locked", False),
        created_at=datetime.now(UTC),
    )
    repo._store[r.id] = r
    return r


async def test_health_ok(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_create_and_get_roundtrip(client, fake_repo):
    c = await client.post("/api/v1/resources", json={"name": "alpha"})
    assert c.status_code == 201, c.text
    body = c.json()
    assert body["name"] == "alpha" and body["locked"] is False

    g = await client.get(f"/api/v1/resources/{body['id']}")
    assert g.status_code == 200
    assert g.json()["id"] == body["id"]


async def test_create_validation_error_is_problem(client):
    r = await client.post("/api/v1/resources", json={"name": ""})
    assert r.status_code == 422
    body = r.json()
    assert r.headers["content-type"] == "application/problem+json"
    assert body["code"] == "VALIDATION.FAILED"
    assert "trace_id" in body


async def test_get_missing_is_problem_not_found(client):
    r = await client.get("/api/v1/resources/nope")
    assert r.status_code == 404
    assert r.json()["code"] == "NOT.FOUND"


async def test_delete_locked_is_conflict(client, fake_repo):
    _seed(fake_repo, locked=True)
    r = await client.delete("/api/v1/resources/res_1")
    assert r.status_code == 409
    assert r.json()["code"] == "CATALOG.RESOURCE_LOCKED"
    # invariant: still locked and present
    assert "res_1" in fake_repo._store


async def test_delete_missing_is_404(client):
    r = await client.delete("/api/v1/resources/nope")
    assert r.status_code == 404
    assert r.json()["code"] == "NOT.FOUND"


# spec: CATALOG.CREATE.IDEMPOTENT_REPLAY
async def test_idempotency_key_replays(client, fake_repo):
    h = {"Idempotency-Key": "key-1"}
    r1 = await client.post("/api/v1/resources", json={"name": "idem"}, headers=h)
    r2 = await client.post("/api/v1/resources", json={"name": "idem"}, headers=h)
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text
    assert r1.json() == r2.json()
    assert len(fake_repo._store) == 1  # no duplicate side effect


# spec: CATALOG.CREATE.IDEMPOTENCY_CONFLICT
async def test_idempotency_key_conflict_on_different_body(client, fake_repo):
    h = {"Idempotency-Key": "key-2"}
    first = await client.post("/api/v1/resources", json={"name": "a"}, headers=h)
    r = await client.post("/api/v1/resources", json={"name": "b"}, headers=h)
    assert first.status_code == 201
    assert r.status_code == 422
    assert r.headers["content-type"] == "application/problem+json"
    assert r.json()["code"] == "VALIDATION.FAILED"
    assert [x.name for x in fake_repo._store.values()] == ["a"]


# spec: CATALOG.CREATE.IDEMPOTENCY_SUBJECT_SCOPE
async def test_idempotency_key_scoped_per_subject(client, fake_repo):
    h = {"Idempotency-Key": "shared-key"}
    other = Principal(subject="another-editor", roles=frozenset({"editor"}))
    mine = await client.post("/api/v1/resources", json={"name": "mine"}, headers=h)
    async with make_client(client.build, principal=other) as c:  # type: ignore[attr-defined]
        theirs = await c.post("/api/v1/resources", json={"name": "theirs"}, headers=h)
    assert mine.status_code == 201 and theirs.status_code == 201, theirs.text
    assert mine.json()["id"] != theirs.json()["id"]
    assert sorted(x.name for x in fake_repo._store.values()) == ["mine", "theirs"]


# spec: CATALOG.CREATE.IDEMPOTENCY_SUBJECT_SCOPE
async def test_idempotency_replay_requires_authorization(client, fake_repo, fake_idempotency):
    from project_backend.modules.catalog.wiring import build_authorizer

    h = {"Idempotency-Key": "editor-key"}
    created = await client.post("/api/v1/resources", json={"name": "owned"}, headers=h)
    assert created.status_code == 201
    viewer = make_client(client.build, principal=VIEWER, authorizer=build_authorizer())  # type: ignore[attr-defined]
    async with viewer as c:
        r = await c.post("/api/v1/resources", json={"name": "owned"}, headers=h)
    assert r.status_code == 403
    assert r.json()["code"] == "AUTHZ.DENIED"
    assert "id" not in r.json()
    assert list(fake_idempotency._store) == [(EDITOR.subject, "editor-key")]
    assert len(fake_repo._store) == 1


async def test_idempotency_key_length_is_validated(client, fake_repo):
    for key in ("", "k" * 65):
        r = await client.post(
            "/api/v1/resources", json={"name": "len"}, headers={"Idempotency-Key": key}
        )
        assert r.status_code == 422, key
        assert r.json()["code"] == "VALIDATION.FAILED"
    assert fake_repo._store == {}


# spec: CATALOG.CREATE.IDEMPOTENCY_EXPIRY
async def test_expired_idempotency_record_is_not_replayed(client, fake_repo, fake_idempotency):
    from project_backend.modules.catalog.application.commands.create_resource import (
        IDEMPOTENCY_TTL,
    )
    from project_backend.modules.catalog.application.ports.repository import IdempotencyRecord

    stale_at = datetime.now(UTC) - IDEMPOTENCY_TTL - timedelta(seconds=1)
    fake_idempotency._store[(EDITOR.subject, "old-key")] = IdempotencyRecord(
        subject=EDITOR.subject,
        key="old-key",
        body_hash="stale",
        status_code=201,
        response_body={"id": "res_gone", "name": "x", "locked": False, "created_at": "x"},
        created_at=stale_at,
    )
    r = await client.post(
        "/api/v1/resources", json={"name": "fresh"}, headers={"Idempotency-Key": "old-key"}
    )
    assert r.status_code == 201, r.text
    assert r.json()["id"] != "res_gone"
    record = fake_idempotency._store[(EDITOR.subject, "old-key")]
    assert record.created_at > stale_at
    assert record.response_body["id"] == r.json()["id"]


# spec: CATALOG.CREATE.IDEMPOTENCY_FAILURE_NOT_STORED
async def test_failed_create_stores_no_idempotency_record(client, fake_repo, fake_idempotency):
    _seed(fake_repo, id="res_taken", name="taken")
    h = {"Idempotency-Key": "dup-key"}
    r = await client.post("/api/v1/resources", json={"name": "taken"}, headers=h)
    assert r.status_code == 422
    assert fake_idempotency._store == {}
    retry = await client.post("/api/v1/resources", json={"name": "free"}, headers=h)
    assert retry.status_code == 201, retry.text
    assert sorted(x.name for x in fake_repo._store.values()) == ["free", "taken"]


async def test_list_pagination_envelope(client, fake_repo):
    _seed(fake_repo, id="res_1", name="one")
    _seed(fake_repo, id="res_2", name="two")
    r = await client.get("/api/v1/resources?page=1&page_size=1")
    body = r.json()
    assert r.status_code == 200
    assert body["total"] == 2 and body["page"] == 1 and body["page_size"] == 1
    assert len(body["items"]) == 1


async def test_unauthenticated_is_401(client, fake_repo):
    # spec: CATALOG.DELETE.UNAUTHENTICATED_401 — real unauthenticated DELETE,
    # no dependency overrides: the real auth path must reject it.
    _seed(fake_repo, id="res_1", name="victim")
    raw_app = client.build  # type: ignore[attr-defined]
    app = raw_app()
    # restore the real principal resolution (conftest overrides it by default)
    app.dependency_overrides.pop(http_deps.get_principal, None)
    import httpx

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.delete("/api/v1/resources/res_1")
    assert r.status_code == 401
    assert r.json()["code"] == "AUTHN.REQUIRED"
    assert r.headers["www-authenticate"].startswith("Bearer")


async def test_deny_has_no_side_effect(client, fake_repo):
    """blueprint 08 §6: deny → 403 + zero business side effects."""
    _seed(fake_repo, id="res_9", name="keep me")
    c = make_client(client.build, principal=VIEWER, authorizer=DenyWrites())  # type: ignore[attr-defined]
    async with c:
        r = await c.delete("/api/v1/resources/res_9")
        assert r.status_code == 403
        assert r.json()["code"] == "AUTHZ.DENIED"
        # no prohibited write happened:
        assert "res_9" in fake_repo._store
        assert fake_repo._store["res_9"].name == "keep me"
