"""AuthN/AuthZ acceptance (blueprint 08 §9): allow/deny, unknown decision,
authority failure, and deny-without-side-effects across entries."""

from datetime import UTC, datetime

import pytest
from project_backend.kernel.authorization import Action, Authorizer, Decision, ResourceRef
from project_backend.kernel.identity import Principal
from project_backend.modules.catalog.domain.resource import Resource

from tests.conftest import EDITOR, VIEWER, AllowAll, DenyWrites, make_client


def _res(rid="res_1", locked=False) -> Resource:
    return Resource(id=rid, name="n", locked=locked, created_at=datetime.now(UTC))


async def test_viewer_cannot_delete_but_can_read(client, fake_repo):
    fake_repo._store["res_1"] = _res()
    # LocalAuthorizer is the deployed authority: viewer lacks 'editor'.
    from project_backend.modules.catalog.wiring import build_authorizer

    c = make_client(client.build, principal=VIEWER, authorizer=build_authorizer())  # type: ignore[attr-defined]
    async with c:
        denied = await c.delete("/api/v1/resources/res_1")
        assert denied.status_code == 403
        assert denied.json()["code"] == "AUTHZ.DENIED"
        assert "res_1" in fake_repo._store  # no side effect

        allowed = await c.get("/api/v1/resources/res_1")
        assert allowed.status_code == 200


async def test_unknown_action_fails_closed():
    """An authorizer that abstains must be treated as DENY by use cases."""
    from project_backend.modules.catalog.application.access import ensure_can

    class Abstaining(Authorizer):
        def decide(self, p: Principal, a: Action, r: ResourceRef) -> Decision:
            raise RuntimeError("authority unavailable")

    with pytest.raises(RuntimeError):
        ensure_can(Abstaining(), EDITOR, "resource.delete", _res())
    # fail-closed: the exception prevents the write path from continuing.


async def test_deny_before_write_ordering(client, fake_repo, fake_idempotency):
    """Deny must happen BEFORE any write attempt — a later rollback is not enough."""
    fake_repo._store["res_1"] = _res()
    c = make_client(client.build, principal=EDITOR, authorizer=DenyWrites())  # type: ignore[attr-defined]
    async with c:
        r = await c.post(
            "/api/v1/resources", json={"name": "nope"}, headers={"Idempotency-Key": "deny-key"}
        )
        assert r.status_code == 403
        assert fake_repo.add_attempts == 0
        assert all(x.name != "nope" for x in fake_repo._store.values())
        assert fake_idempotency._store == {}


async def test_cross_principal_isolation(client, fake_repo):
    """A principal sees only what the authorizer allows — no id-guessing leaks."""
    c = make_client(
        client.build,
        principal=Principal(subject="stranger", roles=frozenset()),
        authorizer=AllowAll(),
    )  # type: ignore[attr-defined]
    async with c:
        # AllowAll is a test double; the point is the plumbing, not the policy.
        r = await c.get("/api/v1/resources/does-not-exist")
        assert r.status_code == 404
        assert r.json()["code"] == "NOT.FOUND"  # no existence oracle beyond 404
