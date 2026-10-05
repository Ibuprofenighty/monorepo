"""Pure domain tests. No DB, no HTTP, no fakes needed (blueprint 10 §2)."""

from datetime import UTC, datetime

import pytest
from project_backend.modules.catalog.domain.errors import ResourceLocked
from project_backend.modules.catalog.domain.resource import Resource


def _res(**kw) -> Resource:
    return Resource(
        id=kw.get("id", "res_1"),
        name=kw.get("name", "n"),
        locked=kw.get("locked", False),
        created_at=datetime.now(UTC),
    )


def test_locked_resource_is_not_deletable():
    with pytest.raises(ResourceLocked):
        _res(locked=True).ensure_deletable()


def test_unlocked_resource_is_deletable():
    _res(locked=False).ensure_deletable()  # no raise


def test_rename_enforces_length():
    with pytest.raises(ValueError):
        _res().rename("")
    assert _res().rename("new name").name == "new name"
