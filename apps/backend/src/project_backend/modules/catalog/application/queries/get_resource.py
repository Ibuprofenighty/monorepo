"""Read use cases. Reads are authorized too (blueprint 08 §5) — just with read policy."""

from __future__ import annotations

from dataclasses import dataclass

from project_backend.kernel.authorization import Action, Authorizer, Decision, ResourceRef
from project_backend.kernel.errors import AuthorizationError
from project_backend.kernel.identity import Principal
from project_backend.modules.catalog.application.ports.repository import UnitOfWork
from project_backend.modules.catalog.domain.errors import ResourceNotFound
from project_backend.modules.catalog.domain.resource import Resource


def ensure_can_read(authorizer: Authorizer, principal: Principal) -> None:
    if (
        authorizer.decide(principal, Action("resource.read"), ResourceRef(kind="resource"))
        is not Decision.ALLOW
    ):
        raise AuthorizationError("denied: resource.read")


@dataclass(frozen=True)
class GetResourceQuery:
    resource_id: str
    principal: Principal


async def get_resource(q: GetResourceQuery, uow: UnitOfWork, authorizer: Authorizer) -> Resource:
    ensure_can_read(authorizer, q.principal)
    async with uow:
        resource = await uow.resources.get(q.resource_id)
    if resource is None:
        raise ResourceNotFound(q.resource_id)
    return resource
