"""STABLE cross-module API (blueprint 04 §3).

Other modules may import ONLY from this file — never from domain/,
application internals, or infrastructure. It exposes use cases with stable
input/output; no SQLAlchemy Session, no ORM objects, no table writes.
"""

from __future__ import annotations

from project_backend.modules.catalog.application.commands.create_resource import (
    CreateResourceCommand,
    create_resource,
    purge_expired_idempotency,
)
from project_backend.modules.catalog.application.commands.delete_resource import (
    DeleteResourceCommand,
    delete_resource,
)
from project_backend.modules.catalog.application.ports.repository import (
    IdempotencyStore,
    ResourceRepository,
    UnitOfWork,
)
from project_backend.modules.catalog.application.queries.get_resource import (
    GetResourceQuery,
    get_resource,
)
from project_backend.modules.catalog.application.queries.list_resources import (
    ListResourcesQuery,
    list_resources,
)
from project_backend.modules.catalog.domain.resource import Resource

__all__ = [
    "Resource",
    "UnitOfWork",
    "ResourceRepository",
    "IdempotencyStore",
    "CreateResourceCommand",
    "create_resource",
    "purge_expired_idempotency",
    "DeleteResourceCommand",
    "delete_resource",
    "GetResourceQuery",
    "get_resource",
    "ListResourcesQuery",
    "list_resources",
]
