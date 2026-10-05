"""Resource entity + invariants. Pure Python: no SQLAlchemy, no Pydantic, no config.

Invariants live here so every entrypoint (HTTP, worker, CLI) enforces them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from project_backend.modules.catalog.domain.errors import ResourceLocked


@dataclass(frozen=True)
class Resource:
    id: str
    name: str
    locked: bool
    created_at: datetime

    def ensure_deletable(self) -> None:
        """INVARIANT CATALOG.DELETE.LOCKED_NO_EFFECT: locked resources cannot be deleted."""
        if self.locked:
            raise ResourceLocked(self.id)

    def rename(self, name: str) -> Resource:
        """Example of a state transition returning a new value (frozen dataclass)."""
        if not name or len(name) > 120:
            raise ValueError("name must be 1..120 chars")
        return Resource(id=self.id, name=name, locked=self.locked, created_at=self.created_at)
