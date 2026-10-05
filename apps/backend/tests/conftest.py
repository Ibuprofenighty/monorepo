"""Shared fixtures. Fakes implement ports — never mock the boundary under test."""

from __future__ import annotations

from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from project_backend.bootstrap.app import create_app
from project_backend.kernel.authorization import Action, Authorizer, Decision, ResourceRef
from project_backend.kernel.identity import Principal
from project_backend.modules.catalog.application.ports.repository import (
    IdempotencyKeyInUse,
    IdempotencyRecord,
)
from project_backend.modules.catalog.domain.errors import DuplicateResource
from project_backend.modules.catalog.domain.resource import Resource
from project_backend.platform.config.settings import Settings
from project_backend.platform.http import deps as http_deps


# ---------- fakes ----------
class FakeRepo:
    """Enforces the unique-name constraint the real table has."""

    def __init__(self) -> None:
        self._store: dict[str, Resource] = {}
        self.add_attempts = 0

    async def get(self, resource_id: str) -> Resource | None:
        return self._store.get(resource_id)

    async def list(self, page: int, page_size: int) -> tuple[list[Resource], int]:
        items = sorted(self._store.values(), key=lambda r: (r.created_at, r.id), reverse=True)
        start = (page - 1) * page_size
        return items[start : start + page_size], len(items)

    async def add(self, resource: Resource) -> None:
        self.add_attempts += 1
        if any(r.name == resource.name for r in self._store.values()):
            raise DuplicateResource(resource.name)
        self._store[resource.id] = resource

    async def remove(self, resource: Resource) -> None:
        self._store.pop(resource.id, None)


class FakeIdempotency:
    """Enforces the (subject, key) primary key the real table has."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], IdempotencyRecord] = {}

    async def get(self, subject: str, key: str) -> IdempotencyRecord | None:
        return self._store.get((subject, key))

    async def add(self, record: IdempotencyRecord) -> None:
        if (record.subject, record.key) in self._store:
            raise IdempotencyKeyInUse(record.key)
        self._store[(record.subject, record.key)] = record

    async def remove(self, subject: str, key: str) -> None:
        self._store.pop((subject, key), None)

    async def purge_created_before(self, cutoff: datetime) -> int:
        expired = [k for k, r in self._store.items() if r.created_at < cutoff]
        for k in expired:
            del self._store[k]
        return len(expired)


class FakeUoW:
    """Transactional fake: writes since the last commit are discarded on rollback/error."""

    def __init__(self, repo: FakeRepo, idempotency: FakeIdempotency) -> None:
        self.resources = repo
        self.idempotency = idempotency
        self.commits = 0
        self._snapshot = self._take()

    def _take(self) -> tuple[dict, dict]:
        return dict(self.resources._store), dict(self.idempotency._store)

    async def commit(self) -> None:
        self.commits += 1
        self._snapshot = self._take()

    async def rollback(self) -> None:
        resources, idem = self._snapshot
        self.resources._store = dict(resources)
        self.idempotency._store = dict(idem)

    async def __aenter__(self) -> FakeUoW:
        self._snapshot = self._take()
        return self

    async def __aexit__(self, *exc: object) -> None:
        if exc[0] is not None:
            await self.rollback()


class AllowAll(Authorizer):
    def decide(self, principal: Principal, action: Action, resource: ResourceRef) -> Decision:
        return Decision.ALLOW


class DenyWrites(Authorizer):
    def decide(self, principal: Principal, action: Action, resource: ResourceRef) -> Decision:
        if action.name in ("resource.create", "resource.delete"):
            return Decision.DENY
        return Decision.ALLOW


EDITOR = Principal(subject="tester", roles=frozenset({"editor"}))
VIEWER = Principal(subject="viewer", roles=frozenset({"viewer"}))


@pytest.fixture
def fake_repo() -> FakeRepo:
    return FakeRepo()


@pytest.fixture
def fake_idempotency() -> FakeIdempotency:
    return FakeIdempotency()


@pytest.fixture
def client(fake_repo: FakeRepo, fake_idempotency: FakeIdempotency, monkeypatch: pytest.MonkeyPatch):
    """ASGI test client with faked persistence. Use make_client(build, principal, authz)."""
    from project_backend.modules.catalog.presentation.http import router as catalog_router

    uow = FakeUoW(fake_repo, fake_idempotency)
    monkeypatch.setattr(catalog_router, "get_uow", lambda session: uow)

    def build(principal: Principal = EDITOR, authorizer: Authorizer | None = None):
        settings = Settings()
        app = create_app(settings)
        app.dependency_overrides[http_deps.get_principal] = lambda: principal
        app.dependency_overrides[http_deps.get_authorizer] = lambda: authorizer or AllowAll()
        app.dependency_overrides[http_deps.get_session] = lambda: object()
        return app

    transport_client = AsyncClient(transport=ASGITransport(app=build()), base_url="http://test")
    transport_client.build = build  # type: ignore[attr-defined]
    return transport_client


def make_client(build, principal: Principal = EDITOR, authorizer: Authorizer | None = None):
    return AsyncClient(
        transport=ASGITransport(app=build(principal, authorizer)), base_url="http://test"
    )


# ---------- markers: applied by directory, selected with -m (not -k) ----------
# -k matches substrings in test names/paths (fragile); markers are explicit.
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    import pathlib

    root = pathlib.Path(__file__).parent
    for item in items:
        rel = str(pathlib.Path(item.path).relative_to(root)).replace("\\", "/")
        marker = None
        if rel.startswith("architecture/"):
            marker = "architecture"
        elif rel.startswith("contract/"):
            marker = "contract"
        elif rel.startswith("integration/"):
            marker = "integration"
        elif rel.startswith("migrations/"):
            marker = "migration"
        elif rel.startswith("security/"):
            marker = "security"
        elif rel.startswith("scaffold/"):
            marker = "unit"
        elif "/unit/" in rel:
            marker = "unit"
        elif "/api/" in rel:
            marker = "api"
        elif "/integration/" in rel:
            marker = "integration"
        if marker:
            item.add_marker(getattr(pytest.mark, marker))
