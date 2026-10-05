"""Domain → generated DTO mapping. Wire format comes from the contract, always."""

from __future__ import annotations

from project_backend.generated.http.models import Resource as ResourceDTO
from project_backend.generated.http.models import ResourceCreate as ResourceCreateDTO
from project_backend.generated.http.models import ResourceList as ResourceListDTO
from project_backend.modules.catalog.domain.resource import Resource


def to_dto(r: Resource) -> ResourceDTO:
    return ResourceDTO(id=r.id, name=r.name, locked=r.locked, created_at=r.created_at)


def to_list_dto(items: list[Resource], total: int, page: int, page_size: int) -> ResourceListDTO:
    return ResourceListDTO(
        items=[to_dto(r) for r in items], total=total, page=page, page_size=page_size
    )


def create_name(body: ResourceCreateDTO) -> str:
    return body.name
