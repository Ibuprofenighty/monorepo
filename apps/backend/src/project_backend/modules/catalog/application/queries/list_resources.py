from __future__ import annotations

from dataclasses import dataclass

from project_backend.kernel.authorization import Authorizer
from project_backend.kernel.identity import Principal
from project_backend.modules.catalog.application.ports.repository import UnitOfWork
from project_backend.modules.catalog.application.queries.get_resource import ensure_can_read
from project_backend.modules.catalog.domain.resource import Resource


@dataclass(frozen=True)
class ListResourcesQuery:
    page: int
    page_size: int
    principal: Principal


async def list_resources(
    q: ListResourcesQuery, uow: UnitOfWork, authorizer: Authorizer
) -> tuple[list[Resource], int]:
    ensure_can_read(authorizer, q.principal)
    async with uow:
        return await uow.resources.list(q.page, q.page_size)
