"""HTTP adapter. Thin: parse → call use case → map. No business decisions here."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from project_backend.generated.http.models import Resource as ResourceDTO
from project_backend.generated.http.models import ResourceCreate as ResourceCreateDTO
from project_backend.generated.http.models import ResourceList as ResourceListDTO
from project_backend.kernel.identity import Principal
from project_backend.modules.catalog.application.commands.create_resource import (
    CreateResourceCommand,
    create_resource,
)
from project_backend.modules.catalog.application.commands.delete_resource import (
    DeleteResourceCommand,
    delete_resource,
)
from project_backend.modules.catalog.application.queries.get_resource import (
    GetResourceQuery,
    get_resource,
)
from project_backend.modules.catalog.application.queries.list_resources import (
    ListResourcesQuery,
    list_resources,
)
from project_backend.modules.catalog.presentation.http import mapping
from project_backend.modules.catalog.presentation.http.error_mapping import to_mapped_error
from project_backend.modules.catalog.wiring import get_uow
from project_backend.platform.http.deps import get_authorizer, get_principal, get_session

router = APIRouter(tags=["catalog"])


@router.get("/resources", response_model=ResourceListDTO)
async def list_resources_ep(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
    authorizer=Depends(get_authorizer),
) -> ResourceListDTO:
    try:
        items, total = await list_resources(
            ListResourcesQuery(page=page, page_size=page_size, principal=principal),
            get_uow(session),
            authorizer,
        )
    except Exception as e:
        raise to_mapped_error(e) from e
    return mapping.to_list_dto(items, total, page, page_size)


@router.post("/resources", response_model=ResourceDTO, status_code=201)
async def create_resource_ep(
    body: ResourceCreateDTO,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
    authorizer=Depends(get_authorizer),
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", min_length=1, max_length=64
    ),
) -> ResourceDTO:
    try:
        resource = await create_resource(
            CreateResourceCommand(
                name=mapping.create_name(body),
                principal=principal,
                idempotency_key=idempotency_key,
            ),
            get_uow(session),
            authorizer,
        )
    except Exception as e:
        raise to_mapped_error(e) from e
    return mapping.to_dto(resource)


@router.get("/resources/{resource_id}", response_model=ResourceDTO)
async def get_resource_ep(
    resource_id: str,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
    authorizer=Depends(get_authorizer),
) -> ResourceDTO:
    try:
        resource = await get_resource(
            GetResourceQuery(resource_id=resource_id, principal=principal),
            get_uow(session),
            authorizer,
        )
    except Exception as e:
        raise to_mapped_error(e) from e
    return mapping.to_dto(resource)


@router.delete("/resources/{resource_id}", status_code=204)
async def delete_resource_ep(
    resource_id: str,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
    authorizer=Depends(get_authorizer),
) -> None:
    try:
        await delete_resource(
            DeleteResourceCommand(resource_id=resource_id, principal=principal),
            get_uow(session),
            authorizer,
        )
    except Exception as e:
        raise to_mapped_error(e) from e
    # 204: no body. Errors surface as problem+json via the mapped handler.
