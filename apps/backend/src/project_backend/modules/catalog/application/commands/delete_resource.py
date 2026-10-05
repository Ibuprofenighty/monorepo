"""Delete resource — protected write use case (blueprint 11 §8 example)."""

from __future__ import annotations

from dataclasses import dataclass

from project_backend.kernel.authorization import Authorizer
from project_backend.kernel.identity import Principal
from project_backend.modules.catalog.application.access import ensure_can
from project_backend.modules.catalog.application.ports.repository import UnitOfWork
from project_backend.modules.catalog.domain.errors import ResourceNotFound


@dataclass(frozen=True)
class DeleteResourceCommand:
    resource_id: str
    principal: Principal


async def delete_resource(
    cmd: DeleteResourceCommand, uow: UnitOfWork, authorizer: Authorizer
) -> None:
    async with uow:
        resource = await uow.resources.get(cmd.resource_id)
        if resource is None:
            raise ResourceNotFound(cmd.resource_id)
        # 1. authorize against trusted facts, 2. enforce domain invariant, 3. write.
        ensure_can(authorizer, cmd.principal, "resource.delete", resource)
        resource.ensure_deletable()
        await uow.resources.remove(resource)
        await uow.commit()
